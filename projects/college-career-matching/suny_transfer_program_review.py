#!/usr/bin/env python3
"""Build a source-preserving SUNY STEP transfer-program review queue.

Institution identity is already reviewed before this stage. Program identity is
not. This module deliberately does NOT infer CIP from program-title similarity.

Input
-----
transfer_agreement_suny_identity.csv

Output
------
suny_transfer_program_review.csv
suny_transfer_program_review_qa.json

One review row represents a unique:
    side + institution UNITID + source program text

The queue preserves how many agreements use that wording and the source
agreement IDs that support it. Degree markers are parsed conservatively for
review convenience; they are not a CIP mapping.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Tuple


DEGREE_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("AAS", re.compile(r"(?<![A-Za-z])A\.?\s*A\.?\s*S\.?(?![A-Za-z])", re.I)),
    ("AOS", re.compile(r"(?<![A-Za-z])A\.?\s*O\.?\s*S\.?(?![A-Za-z])", re.I)),
    ("AS", re.compile(r"(?<![A-Za-z])A\.?\s*S\.?(?![A-Za-z])", re.I)),
    ("AA", re.compile(r"(?<![A-Za-z])A\.?\s*A\.?(?![A-Za-z])", re.I)),
    ("BBA", re.compile(r"(?<![A-Za-z])B\.?\s*B\.?\s*A\.?(?![A-Za-z])", re.I)),
    ("BFA", re.compile(r"(?<![A-Za-z])B\.?\s*F\.?\s*A\.?(?![A-Za-z])", re.I)),
    ("BSN", re.compile(r"(?<![A-Za-z])B\.?\s*S\.?\s*N\.?(?![A-Za-z])", re.I)),
    ("BS", re.compile(r"(?<![A-Za-z])B\.?\s*S\.?(?![A-Za-z])", re.I)),
    ("BA", re.compile(r"(?<![A-Za-z])B\.?\s*A\.?(?![A-Za-z])", re.I)),
    ("MS", re.compile(r"(?<![A-Za-z])M\.?\s*S\.?(?![A-Za-z])", re.I)),
    ("MA", re.compile(r"(?<![A-Za-z])M\.?\s*A\.?(?![A-Za-z])", re.I)),
]


def read_csv(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[Mapping[str, object]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def norm(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).split())


def stable_id(*parts: str) -> str:
    payload = "|".join(norm(part) for part in parts)
    return "SUNY-PROG-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:18]


def parse_degree(program_text: str) -> Tuple[str, str]:
    """Return (canonical degree, normalized title without that degree marker)."""
    text = " ".join((program_text or "").split())
    degree = ""
    title_text = text
    for canonical, pattern in DEGREE_PATTERNS:
        match = pattern.search(text)
        if match:
            degree = canonical
            title_text = (text[: match.start()] + " " + text[match.end() :]).strip()
            break
    return degree, norm(title_text)


def side_fields(side: str) -> Tuple[str, str, str]:
    if side == "sending":
        return (
            "sending_unitid",
            "sending_institution_source_id",
            "sending_program_name",
        )
    if side == "receiving":
        return (
            "receiving_unitid",
            "receiving_institution_source_id",
            "receiving_program_name",
        )
    raise ValueError(f"Unsupported side: {side}")


FIELDS = [
    "program_review_id",
    "side",
    "unitid",
    "institution_source_label",
    "program_text",
    "parsed_degree",
    "normalized_program_title",
    "agreement_count",
    "agreement_ids",
    "source_system",
    "source_url",
    "suggested_cip",
    "suggestion_basis",
    "review_status",
    "reviewed_cip",
    "reviewed_program_id",
    "review_note",
]


def build_review_queue(agreements: List[Mapping[str, str]]) -> Tuple[List[dict], dict]:
    groups: Dict[Tuple[str, str, str], dict] = {}
    missing_text = {"sending": 0, "receiving": 0}

    for row in agreements:
        agreement_id = (row.get("transfer_agreement_id") or "").strip()
        for side in ("sending", "receiving"):
            unitid_col, label_col, program_col = side_fields(side)
            unitid = (row.get(unitid_col) or "").strip()
            label = (row.get(label_col) or "").strip()
            program = (row.get(program_col) or "").strip()

            if not program:
                missing_text[side] += 1
                continue
            if not unitid:
                raise ValueError(
                    f"{agreement_id or '[unknown agreement]'}: {side} program text "
                    "exists but reviewed institution UNITID is missing"
                )

            key = (side, unitid, program)
            if key not in groups:
                degree, normalized_title = parse_degree(program)
                groups[key] = {
                    "program_review_id": stable_id(side, unitid, program),
                    "side": side,
                    "unitid": unitid,
                    "institution_source_label": label,
                    "program_text": program,
                    "parsed_degree": degree,
                    "normalized_program_title": normalized_title,
                    "agreement_ids_set": set(),
                    "source_system": (row.get("source_system") or "SUNY").strip(),
                    "source_url": (row.get("source_url") or "").strip(),
                    "suggested_cip": "",
                    "suggestion_basis": "none — title-only CIP inference prohibited",
                    "review_status": "unreviewed",
                    "reviewed_cip": "",
                    "reviewed_program_id": "",
                    "review_note": "",
                }
            groups[key]["agreement_ids_set"].add(agreement_id)

    out = []
    for item in groups.values():
        ids = sorted(x for x in item.pop("agreement_ids_set") if x)
        item["agreement_count"] = len(ids)
        item["agreement_ids"] = " | ".join(ids)
        out.append(item)
    out.sort(key=lambda r: (r["side"], r["institution_source_label"], r["normalized_program_title"], r["program_text"]))

    ids = [r["program_review_id"] for r in out]
    sending = [r for r in out if r["side"] == "sending"]
    receiving = [r for r in out if r["side"] == "receiving"]
    parsed_degree = sum(bool(r["parsed_degree"]) for r in out)
    qa = {
        "status": "PASS",
        "agreement_count": len(agreements),
        "review_queue_rows": len(out),
        "unique_review_ids": len(set(ids)),
        "duplicate_review_id_count": len(ids) - len(set(ids)),
        "sending_review_rows": len(sending),
        "receiving_review_rows": len(receiving),
        "sending_agreement_rows_missing_program_text": missing_text["sending"],
        "receiving_agreement_rows_missing_program_text": missing_text["receiving"],
        "rows_with_parsed_degree": parsed_degree,
        "auto_assigned_cip_count": sum(bool(r["suggested_cip"] or r["reviewed_cip"]) for r in out),
        "checks": {
            "review_ids_unique": len(ids) == len(set(ids)),
            "unitid_present_for_all_review_rows": all(bool(r["unitid"]) for r in out),
            "source_program_text_preserved": all(bool(r["program_text"]) for r in out),
            "no_title_only_cip_assignment": all(not r["suggested_cip"] and not r["reviewed_cip"] for r in out),
        },
        "guardrail": (
            "Degree parsing is a convenience for review. CIP remains unresolved until "
            "source-published CIP, authoritative institution-program identity, or a "
            "separately reviewed program-name + award-level crosswalk supports it."
        ),
    }
    qa["status"] = "PASS" if all(qa["checks"].values()) else "FAIL"
    return out, qa


def run(input_path: Path, output_path: Path, qa_path: Path) -> dict:
    agreements = read_csv(input_path)
    if not agreements:
        raise ValueError("No transfer agreement rows supplied")
    review, qa = build_review_queue(agreements)
    write_csv(output_path, review, FIELDS)
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(qa, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return qa


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--qa-output", required=True, type=Path)
    args = parser.parse_args()
    qa = run(args.input, args.output, args.qa_output)
    print(json.dumps(qa, indent=2, sort_keys=True))
    return 0 if qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
