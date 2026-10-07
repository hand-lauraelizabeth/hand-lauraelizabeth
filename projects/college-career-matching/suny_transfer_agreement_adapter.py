"""Normalize the public SUNY STEP Transfer Agreement Inventory.

This adapter preserves source wording and does not infer UNITIDs, CIP codes,
admission guarantees, or degree applicability from institution/program names.

Current public-page contract
----------------------------
The live STEP inventory currently exposes:
- ID
- Initial Campus
- Partner Campus
- Type
- Program
- Destination
- Source

For that layout:
- Initial Campus = sending institution
- Partner Campus = receiving institution
- Program = sending/source program wording
- Destination = receiving/destination program wording

A legacy/export layout is also supported where reviewed columns explicitly name
sending/receiving campuses. Ambiguous single-column aliases are never preferred
over the current Initial Campus / Partner Campus pair.

The authoritative source page is:
https://step.transfer.suny.edu/agreements/
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

CANONICAL_FIELDS = [
    "transfer_agreement_id",
    "source_record_id",
    "source_system",
    "sending_institution_source_id",
    "receiving_institution_source_id",
    "sending_unitid",
    "receiving_unitid",
    "agreement_type",
    "agreement_type_raw",
    "sending_program_name",
    "receiving_program_name",
    "source_program_text",
    "destination_program_text",
    "source_link_text",
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
]


def _norm_header(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _first(normalized: Mapping[str, str], aliases: Iterable[str]) -> Optional[str]:
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    return None


def _resolve_columns(fieldnames: Iterable[str]) -> Dict[str, Optional[str]]:
    normalized = {_norm_header(name): name for name in fieldnames if name}

    # Prefer the explicit live-page pair. This prevents the live "Partner Campus"
    # column from being misread as the sender under older export assumptions.
    if "initial campus" in normalized and "partner campus" in normalized:
        resolved: Dict[str, Optional[str]] = {
            "source_record_id": _first(normalized, ["id", "record id", "agreement id"]),
            "sending_institution_source_id": normalized["initial campus"],
            "receiving_institution_source_id": normalized["partner campus"],
            "agreement_type_raw": _first(normalized, ["type", "type description", "agreement type"]),
            "sending_program_name": _first(normalized, ["program", "major or program", "source program"]),
            "receiving_program_name": _first(normalized, ["destination", "destination program", "receiving program"]),
            "source_link_text": _first(normalized, ["source", "source text"]),
        }
    else:
        # Legacy/export contract: only use labels that explicitly identify
        # direction. "Partner Campus" alone is intentionally excluded here.
        resolved = {
            "source_record_id": _first(normalized, ["id", "record id", "agreement id"]),
            "sending_institution_source_id": _first(
                normalized, ["sending campus", "sending institution", "initial campus"]
            ),
            "receiving_institution_source_id": _first(
                normalized, ["4 year partner campus", "4-year partner campus", "receiving campus", "receiving institution"]
            ),
            "agreement_type_raw": _first(normalized, ["type description", "type", "agreement type"]),
            "sending_program_name": _first(normalized, ["major or program", "program", "source program"]),
            "receiving_program_name": _first(normalized, ["destination", "destination program", "receiving program"]),
            "source_link_text": _first(normalized, ["source", "source text"]),
        }

    required = [
        "sending_institution_source_id",
        "receiving_institution_source_id",
        "agreement_type_raw",
        "sending_program_name",
    ]
    missing = [key for key in required if not resolved.get(key)]
    if missing:
        raise ValueError(
            f"Required SUNY STEP fields not found for {missing!r}. "
            f"Available columns: {sorted(normalized)}"
        )
    return resolved


def normalize_agreement_type(raw: str) -> str:
    text = re.sub(r"\s+", " ", (raw or "").strip()).lower()
    if "dual admission" in text:
        return "dual_admission"
    if "dual enrollment" in text:
        return "dual_enrollment"
    if "articulation" in text:
        return "articulation"
    if "major" in text:
        return "major_specific"
    if text in {"n/a", "na", "not applicable"}:
        return "other"
    if "general" in text:
        return "articulation"
    return "other"


def deterministic_id(
    source_record_id: str,
    sending: str,
    receiving: str,
    type_raw: str,
    sending_program: str,
    receiving_program: str,
) -> str:
    if source_record_id:
        return f"SUNY-STEP-{re.sub(r'[^A-Za-z0-9_-]+', '', source_record_id)}"
    payload = "|".join(
        re.sub(r"\s+", " ", value.strip().lower())
        for value in (sending, receiving, type_raw, sending_program, receiving_program)
    )
    return "SUNY-STEP-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _get(row: Mapping[str, str], column: Optional[str]) -> str:
    return (row.get(column) or "").strip() if column else ""


def normalize_row(
    row: Mapping[str, str], columns: Mapping[str, Optional[str]], retrieved_at: str
) -> Dict[str, str]:
    source_record_id = _get(row, columns.get("source_record_id"))
    sending = _get(row, columns.get("sending_institution_source_id"))
    receiving = _get(row, columns.get("receiving_institution_source_id"))
    type_raw = _get(row, columns.get("agreement_type_raw"))
    sending_program = _get(row, columns.get("sending_program_name"))
    receiving_program = _get(row, columns.get("receiving_program_name"))
    source_link_text = _get(row, columns.get("source_link_text"))

    return {
        "transfer_agreement_id": deterministic_id(
            source_record_id, sending, receiving, type_raw, sending_program, receiving_program
        ),
        "source_record_id": source_record_id,
        "source_system": SOURCE_SYSTEM,
        "sending_institution_source_id": sending,
        "receiving_institution_source_id": receiving,
        "sending_unitid": "",
        "receiving_unitid": "",
        "agreement_type": normalize_agreement_type(type_raw),
        "agreement_type_raw": type_raw,
        "sending_program_name": sending_program,
        "receiving_program_name": receiving_program,
        "source_program_text": sending_program,
        "destination_program_text": receiving_program,
        "source_link_text": source_link_text,
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
        "source_version": "public STEP Transfer Agreement Inventory snapshot",
        "evidence_status": "current",
    }


def validate(records: List[Mapping[str, str]]) -> Dict[str, object]:
    ids = [r["transfer_agreement_id"] for r in records]
    missing_sending = sum(not r["sending_institution_source_id"] for r in records)
    missing_receiving = sum(not r["receiving_institution_source_id"] for r in records)
    duplicate_ids = len(ids) - len(set(ids))
    types = Counter(r["agreement_type"] for r in records)
    distinct_sending = len({r["sending_institution_source_id"] for r in records if r["sending_institution_source_id"]})
    distinct_receiving = len({r["receiving_institution_source_id"] for r in records if r["receiving_institution_source_id"]})
    destination_present = sum(bool(r["receiving_program_name"]) for r in records)
    source_ids_present = sum(bool(r["source_record_id"]) for r in records)

    checks = {
        "records_present": len(records) > 0,
        "stable_ids_unique": duplicate_ids == 0,
        "sending_institution_present": missing_sending == 0,
        "receiving_institution_present": missing_receiving == 0,
        "source_url_constant": all(r["source_url"] == SOURCE_URL for r in records),
        "no_unitid_inference_in_adapter": all(not r["sending_unitid"] and not r["receiving_unitid"] for r in records),
        "source_program_text_preserved": all("source_program_text" in r for r in records),
        "destination_program_text_preserved": all("destination_program_text" in r for r in records),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "record_count": len(records),
        "source_record_id_present_count": source_ids_present,
        "duplicate_id_count": duplicate_ids,
        "missing_sending_institution_count": missing_sending,
        "missing_receiving_institution_count": missing_receiving,
        "distinct_sending_institutions": distinct_sending,
        "distinct_receiving_institutions": distinct_receiving,
        "receiving_program_present_count": destination_present,
        "agreement_type_counts": dict(sorted(types.items())),
        "unitid_match_rate_sending": None,
        "unitid_match_rate_receiving": None,
        "program_cip_mapping_rate": None,
        "note": "Identity and CIP coverage are intentionally deferred to reviewed crosswalk stages.",
    }


def run(
    source_file: Path,
    output_file: Path,
    qa_file: Path,
    retrieved_at: Optional[str] = None,
) -> Dict[str, object]:
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
    parser = argparse.ArgumentParser(description="Normalize a SUNY STEP Transfer Agreement Inventory CSV snapshot")
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
