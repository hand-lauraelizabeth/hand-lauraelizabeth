#!/usr/bin/env python3
"""Join normalized SUNY STEP agreements to reviewed institution identity evidence.

This bridge is deliberately conservative:
- only identity rows with match_status == "accepted" contribute UNITID;
- review/unresolved/group rows never receive a forced UNITID;
- source campus wording remains present in the agreement record;
- sending and receiving coverage are reported separately.

Inputs
------
transfer_agreement_suny.csv
suny_institution_identity.csv

Outputs
-------
transfer_agreement_suny_identity.csv
transfer_agreement_suny_identity_qa.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Mapping


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c)).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def read_csv(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[Mapping[str, object]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def accepted_identity_index(rows: Iterable[Mapping[str, str]]) -> Dict[str, Mapping[str, str]]:
    out: Dict[str, Mapping[str, str]] = {}
    collisions = set()
    for row in rows:
        if (row.get("match_status") or "").strip() != "accepted":
            continue
        label = norm(row.get("campus_name_source") or "")
        unitid = (row.get("unitid") or "").strip()
        if not label or not unitid:
            continue
        if label in out and (out[label].get("unitid") or "").strip() != unitid:
            collisions.add(label)
        else:
            out[label] = row
    for label in collisions:
        out.pop(label, None)
    return out


def enrich_agreement(row: Mapping[str, str], idx: Mapping[str, Mapping[str, str]]) -> dict:
    out = dict(row)
    sending = (row.get("sending_institution_source_id") or "").strip()
    receiving = (row.get("receiving_institution_source_id") or "").strip()
    s = idx.get(norm(sending))
    r = idx.get(norm(receiving))

    # Existing adapter fields should be blank at this stage; bridge is the first
    # place accepted identity evidence may populate them.
    out["sending_unitid"] = (s.get("unitid") or "").strip() if s else ""
    out["receiving_unitid"] = (r.get("unitid") or "").strip() if r else ""
    out["sending_identity_status"] = "accepted" if s else "unresolved_or_review"
    out["receiving_identity_status"] = "accepted" if r else "unresolved_or_review"
    out["sending_identity_method"] = (s.get("match_method") or "").strip() if s else ""
    out["receiving_identity_method"] = (r.get("match_method") or "").strip() if r else ""
    return out


def qa(records: List[Mapping[str, str]]) -> Dict[str, object]:
    total = len(records)
    s_ok = sum(bool(r.get("sending_unitid")) for r in records)
    r_ok = sum(bool(r.get("receiving_unitid")) for r in records)
    both = sum(bool(r.get("sending_unitid")) and bool(r.get("receiving_unitid")) for r in records)
    neither = sum(not r.get("sending_unitid") and not r.get("receiving_unitid") for r in records)
    methods = Counter()
    for r in records:
        if r.get("sending_identity_method"):
            methods["sending:" + r["sending_identity_method"]] += 1
        if r.get("receiving_identity_method"):
            methods["receiving:" + r["receiving_identity_method"]] += 1

    checks = {
        "records_present": total > 0,
        "agreement_ids_present": all((r.get("transfer_agreement_id") or "").strip() for r in records),
        "source_labels_preserved": all(
            (r.get("sending_institution_source_id") or "").strip()
            and (r.get("receiving_institution_source_id") or "").strip()
            for r in records
        ),
        "accepted_status_requires_unitid": all(
            (r.get("sending_identity_status") != "accepted" or bool(r.get("sending_unitid")))
            and (r.get("receiving_identity_status") != "accepted" or bool(r.get("receiving_unitid")))
            for r in records
        ),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "agreement_count": total,
        "sending_unitid_matches": s_ok,
        "receiving_unitid_matches": r_ok,
        "both_sides_matched": both,
        "neither_side_matched": neither,
        "sending_match_rate": round(s_ok / total, 6) if total else 0,
        "receiving_match_rate": round(r_ok / total, 6) if total else 0,
        "both_sides_match_rate": round(both / total, 6) if total else 0,
        "match_method_counts": dict(sorted(methods.items())),
        "note": (
            "Coverage rates describe identity resolution only. They are not transfer-quality "
            "scores and unresolved evidence remains in the output."
        ),
    }


def run(agreements_path: Path, identity_path: Path, output_path: Path, qa_path: Path) -> Dict[str, object]:
    agreements = read_csv(agreements_path)
    identities = read_csv(identity_path)
    idx = accepted_identity_index(identities)
    records = [enrich_agreement(row, idx) for row in agreements]
    fields = list(records[0].keys()) if records else [
        "transfer_agreement_id", "sending_institution_source_id",
        "receiving_institution_source_id", "sending_unitid", "receiving_unitid",
        "sending_identity_status", "receiving_identity_status",
        "sending_identity_method", "receiving_identity_method",
    ]
    write_csv(output_path, records, fields)
    report = qa(records)
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--agreements", required=True, type=Path)
    p.add_argument("--identity", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--qa-output", required=True, type=Path)
    args = p.parse_args()
    report = run(args.agreements, args.identity, args.output, args.qa_output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
