"""Normalize the public SUNY STEP Transfer Agreements table.

This adapter intentionally preserves source wording and does not infer UNITIDs,
CIP codes, admission guarantees, or degree applicability from names alone.

Input contract
--------------
A CSV snapshot with these source columns (case/spacing aliases accepted):
- 4 Year Partner Campus OR receiving campus
- Partner Campus OR sending campus
- Type Description OR agreement type
- Major or Program OR program/destination description

The current public STEP page is the authoritative source:
https://step.transfer.suny.edu/agreements/

Usage
-----
python suny_transfer_agreement_adapter.py --source-file step_agreements.csv \
    --output transfer_agreement_suny.csv --qa-output transfer_agreement_suny_qa.json

This is an implementation adapter in the portfolio repository. Successful local
execution against an authoritative snapshot is still required before coverage
counts are treated as production baselines.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

SOURCE_SYSTEM = "SUNY"
SOURCE_URL = "https://step.transfer.suny.edu/agreements/"

ALIASES = {
    "receiving_institution_source_id": [
        "4 year partner campus",
        "4-year partner campus",
        "receiving campus",
        "receiving institution",
    ],
    "sending_institution_source_id": [
        "partner campus",
        "sending campus",
        "sending institution",
    ],
    "agreement_type_raw": ["type description", "type", "agreement type"],
    "program_raw": ["major or program", "program", "destination"],
}

CANONICAL_FIELDS = [
    "transfer_agreement_id",
    "source_system",
    "sending_institution_source_id",
    "receiving_institution_source_id",
    "sending_unitid",
    "receiving_unitid",
    "agreement_type",
    "agreement_type_raw",
    "sending_program_name",
    "receiving_program_name",
    "sending_cip",
    "receiving_cip",
    "sending_degree",
    "receiving_degree",
    "guarantee_type",
    "minimum_grade",
    "effective_start",
    "effective_end",
    "source_url",
    "retrieved_at",
    "source_version",
    "evidence_status",
    "source_program_text",
]


def _norm_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _resolve_columns(fieldnames: Iterable[str]) -> Dict[str, str]:
    normalized = {_norm_header(name): name for name in fieldnames if name}
    resolved: Dict[str, str] = {}
    for target, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                resolved[target] = normalized[alias]
                break
        if target not in resolved:
            raise ValueError(
                f"Required SUNY STEP field not found for {target!r}. "
                f"Available columns: {sorted(normalized)}"
            )
    return resolved


def normalize_agreement_type(raw: str) -> str:
    text = re.sub(r"\s+", " ", (raw or "").strip()).lower()
    if "dual admission" in text:
        return "dual_admission"
    if "dual enrollment" in text:
        return "dual_enrollment"
    if "major" in text:
        return "major_specific"
    if "general" in text or "articulation" in text:
        return "articulation"
    return "other"


def deterministic_id(sending: str, receiving: str, type_raw: str, program: str) -> str:
    payload = "|".join(
        re.sub(r"\s+", " ", value.strip().lower())
        for value in (sending, receiving, type_raw, program)
    )
    return "SUNY-STEP-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def normalize_row(row: Mapping[str, str], columns: Mapping[str, str], retrieved_at: str) -> Dict[str, str]:
    sending = (row.get(columns["sending_institution_source_id"]) or "").strip()
    receiving = (row.get(columns["receiving_institution_source_id"]) or "").strip()
    type_raw = (row.get(columns["agreement_type_raw"]) or "").strip()
    program = (row.get(columns["program_raw"]) or "").strip()

    # The public table currently presents a combined Major/Program description.
    # Preserve it verbatim instead of pretending the sending and receiving
    # programs can always be separated safely.
    return {
        "transfer_agreement_id": deterministic_id(sending, receiving, type_raw, program),
        "source_system": SOURCE_SYSTEM,
        "sending_institution_source_id": sending,
        "receiving_institution_source_id": receiving,
        "sending_unitid": "",
        "receiving_unitid": "",
        "agreement_type": normalize_agreement_type(type_raw),
        "agreement_type_raw": type_raw,
        "sending_program_name": "",
        "receiving_program_name": "",
        "sending_cip": "",
        "receiving_cip": "",
        "sending_degree": "",
        "receiving_degree": "",
        "guarantee_type": "",
        "minimum_grade": "",
        "effective_start": "",
        "effective_end": "",
        "source_url": SOURCE_URL,
        "retrieved_at": retrieved_at,
        "source_version": "public STEP Transfer Agreements snapshot",
        "evidence_status": "current",
        "source_program_text": program,
    }


def validate(records: List[Mapping[str, str]]) -> Dict[str, object]:
    ids = [r["transfer_agreement_id"] for r in records]
    missing_sending = sum(not r["sending_institution_source_id"] for r in records)
    missing_receiving = sum(not r["receiving_institution_source_id"] for r in records)
    duplicate_ids = len(ids) - len(set(ids))
    types = Counter(r["agreement_type"] for r in records)
    distinct_sending = len({r["sending_institution_source_id"] for r in records if r["sending_institution_source_id"]})
    distinct_receiving = len({r["receiving_institution_source_id"] for r in records if r["receiving_institution_source_id"]})

    checks = {
        "records_present": len(records) > 0,
        "stable_ids_unique": duplicate_ids == 0,
        "sending_institution_present": missing_sending == 0,
        "receiving_institution_present": missing_receiving == 0,
        "source_url_constant": all(r["source_url"] == SOURCE_URL for r in records),
        "no_unitid_inference_in_adapter": all(not r["sending_unitid"] and not r["receiving_unitid"] for r in records),
        "source_program_text_preserved": all("source_program_text" in r for r in records),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "record_count": len(records),
        "duplicate_id_count": duplicate_ids,
        "missing_sending_institution_count": missing_sending,
        "missing_receiving_institution_count": missing_receiving,
        "distinct_sending_institutions": distinct_sending,
        "distinct_receiving_institutions": distinct_receiving,
        "agreement_type_counts": dict(sorted(types.items())),
        "unitid_match_rate_sending": None,
        "unitid_match_rate_receiving": None,
        "program_cip_mapping_rate": None,
        "note": "Identity and CIP coverage are intentionally deferred to reviewed crosswalk stages.",
    }


def run(source_file: Path, output_file: Path, qa_file: Path, retrieved_at: Optional[str] = None) -> Dict[str, object]:
    retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    with source_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Source CSV has no header row")
        columns = _resolve_columns(reader.fieldnames)
        records = [normalize_row(row, columns, retrieved_at) for row in reader]

    qa = validate(records)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    qa_file.parent.mkdir(parents=True, exist_ok=True)
    qa_file.write_text(json.dumps(qa, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return qa


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a SUNY STEP Transfer Agreements CSV snapshot")
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--qa-output", required=True, type=Path)
    parser.add_argument("--retrieved-at", default=None)
    args = parser.parse_args()
    qa = run(args.source_file, args.output, args.qa_output, args.retrieved_at)
    print(json.dumps(qa, indent=2, sort_keys=True))
    return 0 if qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
