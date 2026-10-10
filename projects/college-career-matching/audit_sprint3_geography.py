"""S3-02 reproducible Census Gazetteer audit. Research only: aggregate outputs, no public coordinates."""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
import re
import unicodedata
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
URL_ROOT = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2026_Gazetteer/"
SOURCES = {"places": "2026_Gaz_place_national.zip", "zctas": "2026_Gaz_zcta_national.zip"}
OUTPUT = ROOT / "research_aggregate" / "s3_02_aggregate_coverage.json"
NOTES = ROOT / "S3_02_GEOGRAPHY_VALIDATION.md"
FIELDS = {
    "places": {"USPS", "GEOID", "GEOIDFQ", "NAME", "LSAD", "FUNCSTAT", "INTPTLAT", "INTPTLONG"},
    "zctas": {"GEOID", "GEOIDFQ", "INTPTLAT", "INTPTLONG"},
}
SUFFIXES = (" city and borough", " consolidated government (balance)", " urban county",
            " metropolitan government (balance)", " unified government (balance)",
            " zona urbana", " comunidad", " municipality", " village", " borough",
            " town", " city", " cdp")

def normal(v):
    return " ".join(unicodedata.normalize("NFKC", v).casefold().split())

def stem(v):
    n = normal(v)
    for suffix in SUFFIXES:
        if n.endswith(suffix):
            return n[:-len(suffix)].strip()
    return n

def parse(kind):
    req = Request(URL_ROOT + SOURCES[kind],
                  headers={"User-Agent": "CollegeSearch-S3-02/1.0 research audit"})
    with urlopen(req, timeout=90) as response:
        raw = response.read(15_000_001)
        modified = response.headers.get("Last-Modified")
    if not raw.startswith(b"PK") or len(raw) > 15_000_000:
        raise ValueError(kind + ": missing or unexpectedly large ZIP")
    with ZipFile(io.BytesIO(raw)) as z:
        members = [i for i in z.infolist() if i.filename.lower().endswith(".txt")]
        if len(members) != 1 or members[0].file_size > 30_000_000:
            raise ValueError(kind + ": unexpected TXT membership/size")
        member = z.read(members[0])
    text = member.decode("utf-8-sig")
    head = text.splitlines()[0]
    delimiter = "\t" if head.count("\t") > head.count("|") else "|"
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    reader.fieldnames = [s.strip() for s in reader.fieldnames or []]
    if FIELDS[kind] - set(reader.fieldnames):
        raise ValueError(kind + ": missing required columns " + str(FIELDS[kind] - set(reader.fieldnames)))
    rows, ids, states, zeros = [], set(), set(), 0
    for n, raw_row in enumerate(reader, 2):
        row = {k.strip(): (v or "").strip() for k, v in raw_row.items() if k is not None}
        geoid = row["GEOID"]
        if not re.fullmatch(r"\d{5}" if kind == "zctas" else r"\d{7}", geoid) or geoid in ids:
            raise ValueError(kind + ": invalid/duplicate GEOID, row " + str(n))
        ids.add(geoid)
        zeros += geoid.startswith("0")
        if kind == "places":
            if not re.fullmatch("[A-Z]{2}", row["USPS"]) or not row["NAME"]:
                raise ValueError(kind + ": invalid state/name row " + str(n))
            states.add(row["USPS"])
        try:
            lat, lon = float(row["INTPTLAT"]), float(row["INTPTLONG"])
        except ValueError as e:
            raise ValueError(kind + ": invalid internal point at row " + str(n)) from e
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(kind + ": out of range coordinate at row " + str(n))
        rows.append(row)
    metadata = {
        "source_url": URL_ROOT + SOURCES[kind],
        "http_last_modified": modified,
        "zip_sha256": hashlib.sha256(raw).hexdigest(),
        "zip_bytes": len(raw),
        "text_sha256": hashlib.sha256(member).hexdigest(),
        "text_bytes": len(member),
        "text_member": members[0].filename,
        "delimiter": "TAB" if delimiter == "\t" else "PIPE",
        "columns": reader.fieldnames,
        "records": len(rows),
        "unique_geoids": len(ids),
        "valid_internal_points": len(rows),
        "leading_zero_geoids": zeros,
    }
    if kind == "places":
        metadata["states"] = sorted(states)
    return rows, metadata

def college_audit(places):
    raw = (ROOT / "data/sprint2/college-search-national.v2.json").read_bytes()
    schools = json.loads(raw)
    if schools["source_release"] != "2026-06-10" or len(schools["institutions"]) != 6243:
        raise ValueError("Wrong 6,243-school snapshot or vintage")
    by_name = defaultdict(set)
    states = set()
    for row in places:
        by_name[(row["USPS"], stem(row["NAME"]))].add(row["GEOID"])
        states.add(row["USPS"])
    totals, by_state, by_control = Counter(), defaultdict(Counter), defaultdict(Counter)
    examples = defaultdict(list)
    for unitid, school in schools["institutions"].items():
        state, city = school["state"], school["city"]
        candidates = by_name.get((state, normal(city)), set())
        if state not in states:
            category = "outside_places_geography"
        elif not candidates:
            category = "no_exact_place_name"
        elif len(candidates) > 1:
            category = "ambiguous_place_name"
        else:
            category = "unique_city_place_match"
        totals[category] += 1
        by_state[state][category] += 1
        by_control[school["control"] or "unknown"][category] += 1
        if len(examples[category]) < 10 and category != "unique_city_place_match":
            examples[category].append({"unitid": unitid, "city": city, "state": state,
                                       "candidates": len(candidates)})
    assert sum(totals.values()) == 6243
    return {
        "school_sha256": hashlib.sha256(raw).hexdigest(),
        "school_records": 6243,
        "matching_policy": "State-qualified exact normalized School.city to Census Place NAME after limited legal suffix removal; no fuzzy mapping",
        "matched": totals["unique_city_place_match"],
        "matched_percent": round(100 * totals["unique_city_place_match"] / 6243, 2),
        "totals": dict(sorted(totals.items())),
        "by_state": {k: dict(sorted(v.items())) for k, v in sorted(by_state.items())},
        "by_control": {k: dict(sorted(v.items())) for k, v in sorted(by_control.items())},
        "unmatched_examples": dict(sorted(examples.items())),
    }

def main():
    parsed = {}
    meta = {}
    for kind in ("zctas", "places"):
        parsed[kind], meta[kind] = parse(kind)
    match = college_audit(parsed["places"])
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    report = {
        "audit_utc": now,
        "source": "U.S. Census Bureau 2026 Gazetteer",
        "catalog": "https://www.census.gov/geographies/reference-files/2026/geo/gazetter-file.html",
        "schema": "https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/gaz-record-layouts.2026.html",
        "archives": meta,
        "college_city_label_coverage": match,
        "not_measured": ["current USPS ZIP delivery area overlap with ZCTA GEOIDs",
                         "campus street addresses or campus point geocoding",
                         "road/transit/travel time and physically accessible routes"],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# S3-02 — 2026 Census ZIP-area and place validation",
        "",
        "**Source-data audit time:** " + now,
        "",
        "**Scope:** aggregate research evidence only, no campus point or public widget. "
        "The Source ZIP archives were processed in CI; no source ZIP or geography coordinate table "
        "was checked into the public repository.",
        "",
        "## Verified source files",
        "",
        "| Census archive | Records | Distinct GEOIDs | Valid internal points | Archive SHA-256 |",
        "|---|---:|---:|---:|---|",
    ]
    for kind in ("zctas", "places"):
        m = meta[kind]
        lines.append("| " + kind + " | " + str(m["records"]) + " | " + str(m["unique_geoids"])
                     + " | " + str(m["valid_internal_points"]) + " | " + m["zip_sha256"] + " |")
    lines.extend([
        "",
        "See research_aggregate/s3_02_aggregate_coverage.json for original publisher URLs, "
        "ZIP and extracted TXT SHA-256, byte sizes, published HTTP date, member names, "
        "delimiter, schema, supported states and leading-zero GEOIDs. Required fields, "
        "unique 5-digit ZCTA and 7-digit Place GEOIDs, and legal latitude/longitude bounds validated.",
        "",
        "## College Search city-level coverage (not campus coordinates)",
        "",
        str(match["matched"]) + " of 6,243 schools (" + str(match["matched_percent"])
        + "%) resolve to **one** Census Place by conservative normalized city/state label matching.",
        "",
        "| Match outcome | Schools |", "|---|---:|",
    ])
    for cat, count in sorted(match["totals"].items()):
        lines.append("| " + cat.replace("_", " ") + " | " + str(count) + " |")
    lines.extend([
        "",
        "All 6,243 school records remain untouched. No unmatched, ambiguous or out-of-coverage "
        "school was assigned coordinates. No school-city point is represented as a campus coordinate.",
        "",
        "## Limits and follow-up",
        "",
        "Census 2026 Gazetteer ZCTAs use 2020 block geography and **are not USPS postal ZIPs**. "
        "The Census point is an internal point, **not a mathematical centroid** or a reliable campus "
        "location. Census national Places and ZCTAs cover the 50 states, DC and PR; unsupported "
        "island territories remain unresolved. The current valid USPS ZIP denominator is NOT measured.",
        "",
        "Before public distance filtering, review unmatched city aliases independently, verify source "
        "rights and any campus locations, test ZIPs against a suitable current USPS reference, "
        "and assess compressed asset size and accessibility. Sprint 2 release/physical device QA "
        "is independent and still pending. No WordPress changes or public feature claims here.",
        "",
    ])
    NOTES.write_text("\n".join(lines), encoding="utf-8")
    print("S3_02_AUDIT_PASS " + json.dumps({
        "zctas": meta["zctas"]["records"], "places": meta["places"]["records"],
        "matched": match["matched"], "matched_percent": match["matched_percent"],
        "outcomes": match["totals"]}, sort_keys=True))

if __name__ == "__main__":
    main()
