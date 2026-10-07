#!/usr/bin/env python3
"""Resolve SUNY transfer-source campus labels to current IPEDS UNITIDs.

The resolver is conservative by design:
- reviewed STEP-label mappings live in a version-controlled registry;
- every accepted registry mapping must still match the current IPEDS snapshot by
  UNITID, New York state, and normalized institutional name;
- exact current-IPEDS name matches may be accepted;
- token/fuzzy candidates remain review-only and never receive UNITID;
- statutory-college and extension-site source wording is preserved while the
  institution-grain parent UNITID is recorded explicitly.

Outputs preserve unresolved evidence rather than forcing a match.
"""
from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

NY = "NY"
DEFAULT_REVIEWED_ALIASES = Path(__file__).with_name("suny_step_reviewed_aliases.csv")

# Small fallback alias set for non-STEP source variants. The current STEP
# shorthand itself is governed by suny_step_reviewed_aliases.csv.
ALIASES: Dict[str, str] = {
    "suny adirondack": "suny adirondack",
    "suny broome": "suny broome community college",
    "suny cobleskill": "suny college of agriculture and technology at cobleskill",
    "suny delhi": "suny college of technology at delhi",
    "suny esf": "suny college of environmental science and forestry",
    "suny geneseo": "suny college at geneseo",
    "suny maritime": "suny maritime college",
    "suny morrisville": "suny morrisville",
    "suny polytechnic institute": "suny polytechnic institute",
}

GROUP_PATTERNS = [
    re.compile(r"^all\s+suny\s+community\s+colleges?$", re.I),
    re.compile(r"^all\s+suny\b", re.I),
]

SUBUNIT_RE = re.compile(r"^(?P<parent>.+?)\s*\((?P<subunit>[^)]+)\)\s*$")

LEGAL_WORDS = {
    "the", "of", "at", "state", "university", "new", "york", "college",
    "community", "institute", "technology", "school", "campus",
}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c)).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def token_key(value: str) -> Tuple[str, ...]:
    return tuple(sorted(t for t in norm(value).split() if t not in LEGAL_WORDS))


def read_csv(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Iterable[dict], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def candidate_label(row: Mapping[str, str]) -> str:
    for col in ("campus_name", "partner_campus", "four_year_partner", "institution_name"):
        if (row.get(col) or "").strip():
            return (row[col] or "").strip()
    return ""


def classify_label(label: str) -> Tuple[str, str, str]:
    """Return (identity_class, parent_label, subunit_label)."""
    if any(p.search(label.strip()) for p in GROUP_PATTERNS):
        return "institution_group", "", ""
    m = SUBUNIT_RE.match(label.strip())
    if m:
        return "subunit_or_school", m.group("parent").strip(), m.group("subunit").strip()
    return "institution", label.strip(), ""


def build_indexes(ipeds: List[dict]):
    ny_rows = [r for r in ipeds if (r.get("STABBR") or "").strip().upper() == NY]
    exact: Dict[str, List[dict]] = {}
    token: Dict[Tuple[str, ...], List[dict]] = {}
    by_unitid: Dict[str, List[dict]] = {}
    for row in ny_rows:
        exact.setdefault(norm(row.get("INSTNM", "")), []).append(row)
        token.setdefault(token_key(row.get("INSTNM", "")), []).append(row)
        by_unitid.setdefault((row.get("UNITID") or "").strip(), []).append(row)
    return ny_rows, exact, token, by_unitid


def load_reviewed_aliases(
    path: Path,
    ipeds_rows: List[dict],
) -> Dict[str, dict]:
    """Load only accepted aliases after validating them against current IPEDS."""
    if not path.exists():
        return {}
    rows = read_csv(path)
    _, _, _, by_unitid = build_indexes(ipeds_rows)
    out: Dict[str, dict] = {}
    for row in rows:
        if (row.get("review_status") or "").strip().lower() != "accepted":
            continue
        label = (row.get("step_label") or "").strip()
        unitid = (row.get("unitid") or "").strip()
        ipeds_name = (row.get("ipeds_name") or "").strip()
        if not label or not unitid or not ipeds_name:
            raise ValueError(f"Incomplete accepted reviewed alias: {row}")
        candidates = by_unitid.get(unitid, [])
        if len(candidates) != 1:
            raise ValueError(
                f"Reviewed alias {label!r} UNITID {unitid!r} is not unique/present "
                "in the current NY IPEDS reference"
            )
        current = candidates[0]
        if norm(current.get("INSTNM", "")) != norm(ipeds_name):
            raise ValueError(
                f"Reviewed alias {label!r} expected {ipeds_name!r} for UNITID "
                f"{unitid}, but current IPEDS contains {current.get('INSTNM')!r}"
            )
        key = norm(label)
        if key in out and out[key]["unitid"] != unitid:
            raise ValueError(f"Conflicting reviewed aliases for {label!r}")
        merged = dict(row)
        merged["current_ipeds_name"] = current.get("INSTNM", "")
        out[key] = merged
    return out


def base_result(
    row: Mapping[str, str],
    label: str,
    identity_class: str,
    parent: str,
    subunit: str,
) -> dict:
    return {
        "campus_source_id": row.get("campus_source_id", ""),
        "campus_name_source": label,
        "identity_class": identity_class,
        "identity_relationship": "campus",
        "parent_label_for_matching": parent,
        "subunit_label": subunit,
        "unitid": "",
        "ipeds_name": "",
        "match_method": "",
        "match_status": "",
        "candidate_count": 0,
        "source_url": row.get("source_url", ""),
        "review_evidence_url": "",
        "review_note": "",
    }


def resolve(
    row: Mapping[str, str],
    exact: dict,
    token: dict,
    reviewed_aliases: Optional[Mapping[str, Mapping[str, str]]] = None,
) -> dict:
    label = candidate_label(row)
    identity_class, parent, subunit = classify_label(label)
    out = base_result(row, label, identity_class, parent, subunit)

    if identity_class == "institution_group":
        out.update({
            "match_method": "group_not_unitid",
            "match_status": "not_applicable",
            "review_note": "Valid group-level transfer evidence; do not force one UNITID.",
        })
        return out

    reviewed = (reviewed_aliases or {}).get(norm(label))
    if reviewed:
        relationship = (reviewed.get("identity_relationship") or "campus").strip()
        if relationship == "subunit_parent":
            out["identity_class"] = "subunit_or_school"
            out["subunit_label"] = label
        elif relationship == "extension_parent":
            out["identity_class"] = "extension_site"
            out["subunit_label"] = label
        out.update({
            "identity_relationship": relationship,
            "unitid": (reviewed.get("unitid") or "").strip(),
            "ipeds_name": (reviewed.get("current_ipeds_name") or reviewed.get("ipeds_name") or "").strip(),
            "match_method": "reviewed_registry_ny",
            "match_status": "accepted",
            "candidate_count": 1,
            "review_evidence_url": (reviewed.get("suny_evidence_url") or "").strip(),
            "review_note": (reviewed.get("review_note") or "").strip(),
        })
        return out

    match_label = parent or label
    n = norm(match_label)
    alias_target = ALIASES.get(n)
    methods: List[Tuple[str, List[dict]]] = []
    if n:
        methods.append(("exact_name_ny", exact.get(n, [])))
    if alias_target:
        methods.append(("reviewed_alias_ny", exact.get(norm(alias_target), [])))
    if n:
        methods.append(("token_signature_ny", token.get(token_key(match_label), [])))

    for method, candidates in methods:
        if len(candidates) == 1:
            c = candidates[0]
            accepted = method in {"exact_name_ny", "reviewed_alias_ny"}
            out.update({
                "unitid": c.get("UNITID", "") if accepted else "",
                "ipeds_name": c.get("INSTNM", ""),
                "match_method": method,
                "match_status": "accepted" if accepted else "review",
                "candidate_count": 1,
                "review_note": "" if accepted else "Unique token candidate; corroborate before acceptance.",
            })
            return out
        if len(candidates) > 1:
            out.update({
                "match_method": method,
                "match_status": "review",
                "candidate_count": len(candidates),
                "review_note": "Multiple IPEDS candidates; no automatic merge.",
            })
            return out

    out.update({
        "match_method": "unresolved",
        "match_status": "unresolved",
        "review_note": "No evidence-qualified NY IPEDS match.",
    })
    return out


FIELDS = [
    "campus_source_id", "campus_name_source", "identity_class",
    "identity_relationship", "parent_label_for_matching", "subunit_label",
    "unitid", "ipeds_name", "match_method", "match_status", "candidate_count",
    "source_url", "review_evidence_url", "review_note",
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--suny-campuses", required=True, type=Path)
    p.add_argument("--ipeds-hd", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--reviewed-aliases", type=Path, default=DEFAULT_REVIEWED_ALIASES)
    args = p.parse_args()

    suny = read_csv(args.suny_campuses)
    ipeds = read_csv(args.ipeds_hd)
    _, exact, token, _ = build_indexes(ipeds)
    reviewed = load_reviewed_aliases(args.reviewed_aliases, ipeds)
    results = [resolve(r, exact, token, reviewed) for r in suny]

    write_csv(args.output_dir / "suny_institution_identity.csv", results, FIELDS)
    write_csv(
        args.output_dir / "suny_institution_identity_review.csv",
        [r for r in results if r["match_status"] in {"review", "unresolved"}],
        FIELDS,
    )

    total = len(results)
    matchable = sum(r["match_status"] != "not_applicable" for r in results)
    accepted = sum(r["match_status"] == "accepted" for r in results)
    review = sum(r["match_status"] == "review" for r in results)
    unresolved = sum(r["match_status"] == "unresolved" for r in results)
    not_applicable = sum(r["match_status"] == "not_applicable" for r in results)
    subunits = sum(r["identity_class"] in {"subunit_or_school", "extension_site"} for r in results)
    coverage = [{
        "source_rows": total,
        "matchable_rows": matchable,
        "accepted_matches": accepted,
        "review_candidates": review,
        "unresolved": unresolved,
        "group_not_applicable": not_applicable,
        "subunit_or_extension_labels": subunits,
        "accepted_match_rate_of_matchable": round(accepted / matchable, 6) if matchable else 0,
        "review_or_unresolved_rate_of_matchable": round((review + unresolved) / matchable, 6) if matchable else 0,
    }]
    write_csv(
        args.output_dir / "suny_institution_identity_coverage.csv",
        coverage,
        [
            "source_rows", "matchable_rows", "accepted_matches", "review_candidates",
            "unresolved", "group_not_applicable", "subunit_or_extension_labels",
            "accepted_match_rate_of_matchable", "review_or_unresolved_rate_of_matchable",
        ],
    )

    if any(not r["campus_name_source"] for r in results):
        raise SystemExit("QA FAIL: one or more SUNY rows lack a campus label")
    if any(r["match_status"] == "accepted" and not r["unitid"] for r in results):
        raise SystemExit("QA FAIL: accepted match missing UNITID")
    if any(r["match_status"] == "accepted" and r["candidate_count"] != 1 for r in results):
        raise SystemExit("QA FAIL: accepted match is not unique")
    if any(r["identity_class"] == "institution_group" and r["unitid"] for r in results):
        raise SystemExit("QA FAIL: institution group incorrectly assigned UNITID")

    print(
        f"SUNY institution identity: {accepted}/{matchable} matchable accepted; "
        f"{review} review; {unresolved} unresolved; {not_applicable} group N/A"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
