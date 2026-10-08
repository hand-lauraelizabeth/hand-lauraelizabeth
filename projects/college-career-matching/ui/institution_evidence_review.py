"""Audit a private institutional evidence-review CSV without publishing records.

Usage: python institution_evidence_review.py review.csv
Exits 1 when a row is incorrectly marked publishable or when required review
fields are missing for an approved row. Does not independently verify sources.
"""
import csv
import sys
from pathlib import Path

REQUIRED_APPROVED = ("unitid", "institution_name", "setting_source", "housing_source",
                     "aid_source", "access_source", "cohort_map_reference")
BLOCKED = {"DO_NOT_PUBLISH", "PENDING", "UNVERIFIED", "REVIEW_REQUIRED"}
APPROVED = {"APPROVED", "PUBLISH_APPROVED"}


def audit(path):
    errors = []
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return ["Review CSV has no header"], {}
        headers = set(reader.fieldnames)
        if "publication_status" not in headers:
            return ["Review CSV lacks publication_status column"], {}
        counts = {"rows": 0, "blocked": 0, "approved": 0}
        for line, row in enumerate(reader, 2):
            counts["rows"] += 1
            status = (row.get("publication_status") or "").strip().upper()
            if status in BLOCKED:
                counts["blocked"] += 1
            elif status in APPROVED:
                counts["approved"] += 1
                for field in REQUIRED_APPROVED:
                    if not (row.get(field) or "").strip():
                        errors.append(f"Line {line}: approved record lacks {field}")
            else:
                errors.append(f"Line {line}: unknown publication_status {status!r}")
            unitid = (row.get("unitid") or "").strip()
            if unitid and (not unitid.isascii() or not unitid.isdecimal() or len(unitid) != 6):
                errors.append(f"Line {line}: invalid six-digit institution UNITID")
    return errors, counts


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python institution_evidence_review.py review.csv")
    errors, counts = audit(Path(sys.argv[1]))
    for error in errors:
        print(error, file=sys.stderr)
    print(f"Audited {counts.get('rows', 0)} rows; {counts.get('blocked', 0)} blocked; {counts.get('approved', 0)} marked approved.")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
