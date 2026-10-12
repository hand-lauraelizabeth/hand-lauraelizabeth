"""S3-03: research-only place-name reconciliation audit; does not create geocodes.

Fetches pinned 2026 Census Gazetteer Places ZIP (only transient in runner).
All proposed aliases are review candidates, never assignments or location proof.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from audit_sprint3_geography import ROOT, parse, normal, stem

BASELINE_FILE = ROOT / "research_aggregate/s3_02_aggregate_coverage.json"
SCHOOLS_FILE = ROOT / "data/sprint2/college-search-national.v2.json"
SUMMARY_FILE = ROOT / "research_aggregate/s3_03_identity_summary.json"
REVIEW_QUEUE_FILE = ROOT / "research_work/s3_03_review_queue.json"
DOCUMENT_FILE = ROOT / "S3_03_IDENTITY_REVIEW.md"

REPLACE_FIRST = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "ft": "fort", "mt": "mount", "st": "saint",
}
def tokens(label):
    """Conservative punctuation folding, without inventing alternative place labels."""
    ascii_label = "".join(c for c in unicodedata.normalize("NFKD", label)
                          if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", ascii_label.casefold()))

def candidate_queries(city, state):
    """Generate bounded *review probes* only; returned strings are never geocodes."""
    base = tokens(city)
    statesfx = state.casefold()
    results = {"punctuation_or_diacritic": {base}}
    # School label explicitly repeats its own two-letter state: remove only that exact marker.
    if base.endswith(" " + statesfx):
        results["redundant_state_suffix"] = {base[:-(len(statesfx) + 1)]}
    first, sep, rest = base.partition(" ")
    if sep and first in REPLACE_FIRST:
        results["initial_abbreviation"] = {REPLACE_FIRST[first] + " " + rest}
    # Do not use broad edit-distance, fuzzy matching, substrings, or nationwide city names.
    return {k: vals for k, vals in results.items() if vals}

def run():
    old = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    rows, meta = parse("places")
    pinned = old["archives"]["places"]
    for field in ("zip_sha256", "text_sha256", "records", "unique_geoids"):
        if meta[field] != pinned[field]:
            raise RuntimeError("Gazetteer 2026 Places source drift on " + field)
    raw = SCHOOLS_FILE.read_bytes()
    schools = json.loads(raw)["institutions"]
    if hashlib.sha256(raw).hexdigest() != old["college_city_label_coverage"]["school_sha256"]:
        raise RuntimeError("S3-02 College Scorecard input changed")
    if len(schools) != 6243:
        raise RuntimeError("Expected 6,243 UNITIDs")
    exact = defaultdict(list)
    punctuation = defaultdict(set)
    for row in rows:
        canonical = (row["USPS"], stem(row["NAME"]))
        exact[canonical].append(row)
        punctuation[(row["USPS"], tokens(stem(row["NAME"])))].add(row["GEOID"])
    all_by_geoid = {row["GEOID"]: row for row in rows}
    census_states = set(meta["states"])
    categories = Counter()
    by_state = defaultdict(Counter)
    by_control = defaultdict(Counter)
    missing_city_frequency = defaultdict(Counter)
    query_types = Counter()
    probe_result = Counter()
    eligible_unique = {}
    examples = defaultdict(list)
    full_queue = []
    ambiguous_geoid_pairs = Counter()
    for unitid, school in schools.items():
        state, city, control = school["state"], school["city"], school["control"] or "unknown"
        direct = exact.get((state, normal(city)), [])
        if state not in census_states:
            kind = "outside_places_geography"
        elif not direct:
            kind = "no_exact_place_name"
        elif len(direct) > 1:
            kind = "ambiguous_place_name"
        else:
            kind = "unique_city_place_match"
        categories[kind] += 1
        by_state[state][kind] += 1
        by_control[control][kind] += 1
        if kind == "unique_city_place_match":
            continue
        item = {"unitid": unitid, "city": city, "state": state, "baseline_category": kind}
        if kind == "no_exact_place_name":
            missing_city_frequency[state][city] += 1
            for probe_type, values in candidate_queries(city, state).items():
                possible = set()
                for value in values:
                    possible.update(punctuation.get((state, value), set()))
                if not possible:
                    continue
                query_types[probe_type] += 1
                item.setdefault("probes", {})[probe_type] = [
                    {"geoid": code, "census_name": all_by_geoid[code]["NAME"],
                     "lsad": all_by_geoid[code]["LSAD"]}
                    for code in sorted(possible)]
            joined = {c["geoid"] for matches in item.get("probes", {}).values() for c in matches}
            if len(joined) == 1:
                probe_result["one_official_place_candidate"] += 1
                code = next(iter(joined))
                eligible_unique[unitid] = code
            elif len(joined) > 1:
                probe_result["multiple_official_place_candidates"] += 1
            else:
                probe_result["no_official_place_candidate"] += 1
        elif kind == "ambiguous_place_name":
            item["official_place_options"] = [
                {"geoid": v["GEOID"], "census_name": v["NAME"], "lsad": v["LSAD"]}
                for v in sorted(direct, key=lambda z:z["GEOID"])]
            ambiguous_geoid_pairs[(state, normal(city))] += 1
        # These are public source identities, not geocodes or student/user records.
        full_queue.append(item)
        if len(examples[kind]) < 14:
            examples[kind].append(item)
    if categories != Counter(old["college_city_label_coverage"]["totals"]):
        raise RuntimeError("Regression: S3-02 classification no longer matches " + repr(categories))
    assert len(full_queue) == 584
    assert categories["no_exact_place_name"] == 553
    assert categories["ambiguous_place_name"] == 20
    assert categories["outside_places_geography"] == 11
    assert sum(probe_result.values()) == 553
    assert len(eligible_unique) == probe_result["one_official_place_candidate"]

    # "One Census place candidate" is not evidence of a campus location.
    unique_names = len({(x["state"], x["city"]) for x in full_queue})
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    report = {
        "audit_utc": now,
        "source_url": meta["source_url"], "source_archive_sha256": meta["zip_sha256"],
        "college_sha256": hashlib.sha256(raw).hexdigest(),
        "denominator_colleges": 6243, "baseline_matched": 5659,
        "baseline_unresolved": 584,
        "unresolved_distinct_state_city_pairs": unique_names,
        "baseline_categories": dict(sorted(categories.items())),
        "candidate_policy": "Unique official Census name candidates are unverified proposals; never auto-assign a GEOID or coordinate.",
        "no_exact_probes": dict(sorted(probe_result.items())),
        "probe_hits_by_type_not_disjoint": dict(sorted(query_types.items())),
        "unique_candidate_max_if_each_later_approved": len(eligible_unique),
        "hypothetical_only_coverage_max": 5659 + len(eligible_unique),
        "by_state_unresolved": {s: dict(sorted(x.items())) for s,x in sorted(by_state.items())
                                if any(k != "unique_city_place_match" for k in x)},
        "by_control_unresolved": {s: dict(sorted((k,v) for k,v in x.items()
                                   if k != "unique_city_place_match")) for s,x in sorted(by_control.items())},
        "top_issues_by_state": {
            state: [{"city": city, "records": count}
                    for city, count in sorted(cs.items(), key=lambda z:(-z[1], z[0]))[:20]]
            for state,cs in sorted(missing_city_frequency.items()) if state in {"NY", "PR", "NJ", "CA"}},
        "ambiguous_distinct_state_city_pairs": len(ambiguous_geoid_pairs),
        "examples": {k:v for k,v in sorted(examples.items())},
        "not_approved": [
            "campus coordinates", "automatic match of candidate labels",
            "full current USPS ZIP match rate", "campus-address verification",
            "Haversine distance", "new UI control", "Sprint 2 release"
        ],
    }
    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)+"\n",
                            encoding="utf-8")
    REVIEW_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_QUEUE_FILE.write_text(json.dumps({"generated_at":now, "items":full_queue},
                            indent=2, sort_keys=True, ensure_ascii=False)+"\n", encoding="utf-8")
    notes = [
        "# S3-03 — Geographic identity mismatch review (research only)", "",
        "**Completed source pass:** " + now, "",
        "Compared the *same SHA-256-pinned* Census 2026 Gazetteer Places archive and the "
        "same verified 6,243-institution College Scorecard snapshot as S3-02. "
        "The 584 unresolved school records are reviewed as public-source city/state labels, "
        "**not** personal addresses or verified campuses. The full non-coordinate review queue "
        "is a CI artifact only (not committed as a publicly browsable review list).", "",
        "## Baseline remains unchanged", "",
        "| Outcome | Schools |", "|---|---:|",
    ]
    for category,count in sorted(categories.items()):
        notes.append("| "+category.replace("_"," ")+" | "+str(count)+" |")
    notes.extend([
        "", "## Alternative official-place-name *review probes* for 553 no-exact matches", "",
        "Only exact equality to another **published 2026 Census Place name** within the "
        "same state is considered, with narrowly bounded punctuation/diacritic folding, "
        "an explicit redundant state-code suffix, or a first-token directional/name "
        "abbreviation. These probes are **candidates for manual source review**, never "
        "accepted coordinates or confirmed alternative campus addresses.", "",
        "| Probe result | Schools |", "|---|---:|",
    ])
    for k,v in sorted(probe_result.items()):
        notes.append("| "+k.replace("_"," ")+" | "+str(v)+" |")
    notes.extend([
        "",
        "**Hypothetical ceiling only, not an implemented result:** if every single-candidate "
        "probe were independently confirmed later, no more than "+
        str(5659+len(eligible_unique))+" of 6,243 school-city labels could be linked "
        "on this limited check. Actual verified and deployed match count is still **5,659**.",
        "",
        "## Ambiguity and outside-coverage boundaries", "",
        str(categories["ambiguous_place_name"])+" school records match more than one "
        "published same-state Census Place; "+str(len(ambiguous_geoid_pairs))+
        " distinct city/state labels are affected. Multiple legal/statistical places "
        "sharing a name cannot be resolved from the college city/state string alone. "
        "No arbitrary preference for city, CDP, incorporated place or one GEOID is allowed.",
        "",
        str(categories["outside_places_geography"])+" school records reside in state/territory "
        "codes absent from the national Census Places archive. No nearby substitute or "
        "foreign/country-level centroid is assigned.", "",
        "## Largest unresolved areas and likely review priorities", "",
    ])
    for state in ("NY","PR","NJ","CA"):
        cs=missing_city_frequency.get(state, {})
        notes.append("- **"+state+"**: "+str(sum(cs.values()))+
                     " no-exact school records; most frequent raw labels: "+
                     ", ".join(city+" ("+str(count)+")"
                              for city,count in sorted(cs.items(),key=lambda z:(-z[1],z[0]))[:10]))
    notes.extend([
        "", "Top raw labels are *investigation leads*, **not** proof that the school "
        "campus is inside a Census Place or that the Scorecard city field is wrong. "
        "Full triage is available in the aggregate JSON and CI review artifact.", "",
        "## Required independent evidence before any acceptance", "",
        "For each candidate obtain a current authoritative *institution campus address* "
        "or accepted campus location data linked explicitly by UNITID, plus an authoritative "
        "municipality/census identity crosswalk as needed. Check date, main-vs-branch-campus "
        "identity, state, legal place type and possibly multiple campuses. Retain null for "
        "unconfirmed or unsupported cases. Census internal points are city-area proxies only, "
        "not campus points or transportation distances.", "",
        "## Release and data boundaries", "",
        "No official place coordinates, raw Census ZIP files, resolved school geocodes, "
        "distance control or new browser asset were committed. Therefore there is **no "
        "Sprint 3 browser gzip-budget measurement** and **no verified current-USPS-ZIP "
        "coverage**. Sprint 2 remains a private draft under separate mobile/authenticated "
        "QA and explicit approval gates. No WordPress edits or publication.", "",
        "Source: [Census Bureau 2026 Gazetteer](https://www.census.gov/geographies/reference-files/2026/geo/gazetter-file.html) "
        "and [2026 record layout](https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/gaz-record-layouts.2026.html).",
        "",
    ])
    DOCUMENT_FILE.write_text("\n".join(notes), encoding="utf-8")
    print("S3_03_IDENTITY_AUDIT_PASS "+json.dumps({
        "unresolved":len(full_queue), "distinct_labels":unique_names,
        "one_candidate":probe_result["one_official_place_candidate"],
        "multi_candidate":probe_result["multiple_official_place_candidates"],
        "no_candidate":probe_result["no_official_place_candidate"],
        "ambiguous":20,"outside":11,
    },sort_keys=True))
if __name__ == "__main__":
    run()
