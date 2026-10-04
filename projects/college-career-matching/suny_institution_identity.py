#!/usr/bin/env python3
"""Resolve SUNY transfer-source campus labels to IPEDS UNITID candidates.

This module is deliberately conservative. It produces accepted matches only when
rules meet explicit evidence thresholds; otherwise it emits a review queue.
It is designed to sit between SUNY STEP adapters and the existing IPEDS-backed
institution model.

Expected SUNY input columns (one or more label columns may be supplied):
    campus_source_id, campus_name, source_url

Expected IPEDS reference columns:
    UNITID, INSTNM, STABBR, CITY, WEBADDR

Outputs:
    suny_institution_identity.csv
    suny_institution_identity_review.csv
    suny_institution_identity_coverage.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

NY = "NY"

# Source-name aliases should be evidence-backed and reviewed. Keep this table
# intentionally small; additions require a source/review note in version control.
ALIASES: Dict[str, str] = {
    "suny adirondack": "adirondack community college",
    "suny broome": "suny broome community college",
    "suny cobleskill": "suny college of agriculture and technology at cobleskill",
    "suny cortland": "suny cortland",
    "suny delhi": "suny college of technology at delhi",
    "suny esf": "suny college of environmental science and forestry",
    "suny geneseo": "suny college at geneseo",
    "suny maritime": "suny maritime college",
    "suny morrisville": "morrisville state college",
    "suny new paltz": "suny new paltz",
    "suny old westbury": "suny old westbury",
    "suny oneonta": "suny oneonta",
    "suny oswego": "suny oswego",
    "suny plattsburgh": "suny plattsburgh",
    "suny potsdam": "suny potsdam",
    "suny polytechnic institute": "suny polytechnic institute",
}

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
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def candidate_label(row: dict) -> str:
    for col in ("campus_name", "partner_campus", "four_year_partner", "institution_name"):
        if (row.get(col) or "").strip():
            return row[col].strip()
    return ""


def build_indexes(ipeds: List[dict]):
    ny_rows = [r for r in ipeds if (r.get("STABBR") or "").strip().upper() == NY]
    exact: Dict[str, List[dict]] = {}
    token: Dict[Tuple[str, ...], List[dict]] = {}
    for row in ny_rows:
        exact.setdefault(norm(row.get("INSTNM", "")), []).append(row)
        token.setdefault(token_key(row.get("INSTNM", "")), []).append(row)
    return ny_rows, exact, token


def resolve(row: dict, exact: dict, token: dict) -> dict:
    label = candidate_label(row)
    n = norm(label)
    alias_target = ALIASES.get(n)
    methods: List[Tuple[str, List[dict]]] = []

    if n:
        methods.append(("exact_name_ny", exact.get(n, [])))
    if alias_target:
        methods.append(("reviewed_alias_ny", exact.get(norm(alias_target), [])))
    if n:
        methods.append(("token_signature_ny", token.get(token_key(label), [])))

    for method, candidates in methods:
        if len(candidates) == 1:
            c = candidates[0]
            # Exact and reviewed aliases can auto-accept. Token signatures remain
            # candidates because removing generic institution words can overmerge.
            accepted = method in {"exact_name_ny", "reviewed_alias_ny"}
            return {
                "campus_source_id": row.get("campus_source_id", ""),
                "campus_name_source": label,
                "unitid": c.get("UNITID", ""),
                "ipeds_name": c.get("INSTNM", ""),
                "match_method": method,
                "match_status": "accepted" if accepted else "review",
                "candidate_count": 1,
                "source_url": row.get("source_url", ""),
                "review_note": "" if accepted else "Unique token candidate; corroborate before acceptance.",
            }
        if len(candidates) > 1:
            return {
                "campus_source_id": row.get("campus_source_id", ""),
                "campus_name_source": label,
                "unitid": "",
                "ipeds_name": "",
                "match_method": method,
                "match_status": "review",
                "candidate_count": len(candidates),
                "source_url": row.get("source_url", ""),
                "review_note": "Multiple IPEDS candidates; no automatic merge.",
            }

    return {
        "campus_source_id": row.get("campus_source_id", ""),
        "campus_name_source": label,
        "unitid": "",
        "ipeds_name": "",
        "match_method": "unresolved",
        "match_status": "unresolved",
        "candidate_count": 0,
        "source_url": row.get("source_url", ""),
        "review_note": "No evidence-qualified NY IPEDS match.",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--suny-campuses", required=True, type=Path)
    p.add_argument("--ipeds-hd", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()

    suny = read_csv(args.suny_campuses)
    ipeds = read_csv(args.ipeds_hd)
    _, exact, token = build_indexes(ipeds)

    results = [resolve(r, exact, token) for r in suny]
    fields = [
        "campus_source_id", "campus_name_source", "unitid", "ipeds_name",
        "match_method", "match_status", "candidate_count", "source_url", "review_note",
    ]
    write_csv(args.output_dir / "suny_institution_identity.csv", results, fields)
    write_csv(
        args.output_dir / "suny_institution_identity_review.csv",
        [r for r in results if r["match_status"] != "accepted"],
        fields,
    )

    total = len(results)
    accepted = sum(r["match_status"] == "accepted" for r in results)
    review = sum(r["match_status"] == "review" for r in results)
    unresolved = sum(r["match_status"] == "unresolved" for r in results)
    coverage = [{
        "source_rows": total,
        "accepted_matches": accepted,
        "review_candidates": review,
        "unresolved": unresolved,
        "accepted_match_rate": round(accepted / total, 6) if total else 0,
        "review_or_unresolved_rate": round((review + unresolved) / total, 6) if total else 0,
    }]
    write_csv(
        args.output_dir / "suny_institution_identity_coverage.csv",
        coverage,
        ["source_rows", "accepted_matches", "review_candidates", "unresolved", "accepted_match_rate", "review_or_unresolved_rate"],
    )

    # Structural QA only. Coverage floors must be set after the first authoritative
    # snapshot, never guessed before execution.
    if any(not r["campus_name_source"] for r in results):
        raise SystemExit("QA FAIL: one or more SUNY rows lack a campus label")
    if any(r["match_status"] == "accepted" and not r["unitid"] for r in results):
        raise SystemExit("QA FAIL: accepted match missing UNITID")
    if any(r["match_status"] == "accepted" and r["candidate_count"] != 1 for r in results):
        raise SystemExit("QA FAIL: accepted match is not unique")

    print(f"SUNY institution identity: {accepted}/{total} accepted; {review} review; {unresolved} unresolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
