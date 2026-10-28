"""Private NYC 311 source-receipt to 20-cell reconciliation (publication HOLD).

Binds an independently audited seven-field private CSV receipt to the supplied
five-borough/four-group editorial manifest. A match proves internal arithmetic,
NOT immutable publisher provenance, auxiliary-table safety or disclosure safety.
Never commit private inputs or print source counts, agency labels, or keys.
"""
import argparse
import hashlib
import json
from pathlib import Path

from coarse_20cell_binding_audit import audit as audit_coarse
from source_receipt_audit import audit as audit_source

BLOCKING = {
    "invalid_coarse_binding_schema", "unexpected_source_borough",
    "duplicate_fine_group", "unmapped_source_agency", "duplicate_coarse_cell",
    "incomplete_or_extra_coarse_grid", "coarse_counts_do_not_reconcile",
    "excluded_borough_count_mismatch", "source_total_count_mismatch",
    "coarse_cell_below_display_threshold", "source_digest_mismatch",
}
HOLD = "OFFICIAL_PROVENANCE_AND_DISCLOSURE_REVIEW_PENDING"


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(private_csv, private_receipt, private_manifest):
    """Return redacted finding codes only; never source data."""
    findings = {HOLD}
    try:
        receipt_bytes = Path(private_receipt).read_bytes()
        source_codes = audit_source(private_csv, private_receipt)
        if "INTERNAL_RECEIPT_CONSISTENCY_VERIFIED" not in source_codes:
            return sorted(findings | {"SOURCE_RECEIPT_AUDIT_FAILED"})
        if Path(private_receipt).read_bytes() != receipt_bytes:
            return sorted(findings | {"RECEIPT_CHANGED_DURING_BINDING"})
        receipt = json.loads(receipt_bytes)
        manifest = json.loads(Path(private_manifest).read_text(encoding="utf-8"))
        coarse_codes = set(audit_coarse(manifest, receipt["csv_sha256"]))
        if "invalid_coarse_binding_schema" in coarse_codes:
            return sorted(findings | {"COARSE_BINDING_INVALID_OR_UNSAFE"})
        if coarse_codes & BLOCKING:
            findings.add("COARSE_BINDING_INVALID_OR_UNSAFE")
        if manifest["month"] != receipt["reporting_month"]:
            findings.add("REPORTING_MONTH_MISMATCH")
        fine = manifest["fine_rows"]
        if any(type(r["requests"]) is not int or r["requests"] <= 0 for r in fine):
            findings.add("FINE_SOURCE_GROUP_INVALID")
        if len(fine) != receipt["aggregate_cells"]:
            findings.add("SOURCE_GROUP_COVERAGE_MISMATCH")
        if sum(r["requests"] for r in fine) != receipt["rows"]:
            findings.add("SOURCE_ROW_TOTAL_MISMATCH")
        if manifest["source_total_requests"] != receipt["rows"]:
            findings.add("DECLARED_SOURCE_TOTAL_MISMATCH")
        canonical = [[r["borough"], r["agency"], r["requests"]]
                     for r in sorted(fine, key=lambda r: (r["borough"], r["agency"]))]
        digest = hashlib.sha256(json.dumps(
            canonical, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        if digest != receipt["aggregate_sha256"]:
            findings.add("SOURCE_AGGREGATE_DIGEST_MISMATCH")
        if _file_sha256(private_csv) != receipt["csv_sha256"]:
            findings.add("SOURCE_CHANGED_DURING_BINDING")
        if len(findings) == 1:
            findings.add("PRIVATE_SOURCE_TO_20_CELL_ARITHMETIC_VERIFIED")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, OverflowError):
        findings.add("RECONCILIATION_INPUT_UNREADABLE_OR_INVALID")
    return sorted(findings)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_csv", type=Path)
    parser.add_argument("private_receipt", type=Path)
    parser.add_argument("private_coarse_manifest", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps({"hold": True, "publication_approved": False,
                      "codes": audit(args.private_csv, args.private_receipt,
                                     args.private_coarse_manifest)}, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
