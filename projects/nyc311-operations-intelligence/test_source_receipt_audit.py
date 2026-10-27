"""Synthetic-only adversarial tests for independent NYC 311 receipt auditing."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from collections import Counter

from source_receipt_audit import FIELDS, audit, main


class ReceiptAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.csvfile = Path(self.tmp.name) / "source.csv"
        self.receiptfile = Path(self.tmp.name) / "receipt.json"
        self.rows = [
            ["0001", "2026-09-01T00:00:00", "", "Agency A", "Category X", "QUEENS", "Open"],
            ["0002", "2026-09-15T12:30:00", "", "Agency B", "Category Y", "BROOKLYN", "Closed"],
            ["0003", "2026-09-30T23:59:59", "", "Agency A", "Category X", "QUEENS", "Open"],
        ]
        self.write()

    def write(self):
        with self.csvfile.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(FIELDS)
            w.writerows(self.rows)
        pairs = Counter((r[5], r[3]) for r in self.rows)
        pair_digest = hashlib.sha256(json.dumps(
            [[b, a, n] for (b, a), n in sorted(pairs.items())],
            separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        self.receipt = {
            "dataset": "erm2-nwe9",
            "reporting_month": "2026-09",
            "publisher": "https://data.cityofnewyork.us/d/erm2-nwe9",
            "fields": list(FIELDS), "ordered_by": "unique_key ASC",
            "cross_aggregate_verified": True, "release_status": "HOLD",
            "rows": len(self.rows), "distinct_keys": len({r[0] for r in self.rows}),
            "aggregate_cells": len(pairs), "publisher_rows_updated_at": 1790000000,
            "csv_sha256": hashlib.sha256(self.csvfile.read_bytes()).hexdigest(),
            "aggregate_sha256": pair_digest,
        }
        self.save_receipt()

    def save_receipt(self):
        self.receiptfile.write_text(json.dumps(self.receipt), encoding="utf-8")

    def codes(self):
        return audit(self.csvfile, self.receiptfile)

    def test_valid_receipt_is_still_publication_hold(self):
        self.assertEqual(self.codes(), [
            "DISCLOSURE_AND_TEMPORAL_REVIEW_PENDING",
            "INTERNAL_RECEIPT_CONSISTENCY_VERIFIED",
            "OFFICIAL_SOURCE_ORIGIN_NOT_AUTHENTICATED",
        ])
        self.assertEqual(main([str(self.csvfile), str(self.receiptfile)]), 2)

    def test_tampered_csv_fails_digest(self):
        self.csvfile.write_bytes(self.csvfile.read_bytes().replace(b"Category Y", b"Category Z"))
        self.assertIn("CSV_SHA256_MISMATCH", self.codes())

    def test_forged_aggregate_digest_fails(self):
        self.receipt["aggregate_sha256"] = "0" * 64
        self.save_receipt()
        self.assertIn("AGGREGATE_SHA256_MISMATCH", self.codes())

    def test_balanced_borough_agency_mutation_fails_aggregate_even_with_new_csv_hash(self):
        self.rows[1][5] = "QUEENS"
        self.write()
        self.receipt["aggregate_sha256"] = "f" * 64
        self.save_receipt()
        self.assertIn("AGGREGATE_SHA256_MISMATCH", self.codes())

    def test_duplicate_key_fails_even_if_receipt_is_recalculated(self):
        self.rows[1][0] = "0001"
        self.write()
        self.assertIn("KEY_DUPLICATE_OR_ORDER_INVALID", self.codes())

    def test_out_of_month_fails_even_if_hashes_match(self):
        self.rows[2][1] = "2026-10-01T00:00:00"
        self.write()
        self.assertIn("CREATED_DATE_OUTSIDE_MONTH", self.codes())

    def test_tz_bearing_date_fails(self):
        self.rows[0][1] = "2026-09-01T00:00:00+00:00"
        self.write()
        self.assertIn("CREATED_DATE_OUTSIDE_MONTH", self.codes())

    def test_row_count_mismatch(self):
        self.receipt["rows"] = 4
        self.receipt["distinct_keys"] = 4
        self.save_receipt()
        self.assertIn("ROW_OR_DISTINCT_KEY_COUNT_MISMATCH", self.codes())

    def test_header_and_malformed_row_fail(self):
        self.csvfile.write_text("bad,header\n1,2\n", encoding="utf-8")
        self.assertIn("CSV_UNREADABLE_OR_MALFORMED", self.codes())

    def test_invalid_receipt_rejected(self):
        self.receipt["release_status"] = "APPROVED"
        self.save_receipt()
        self.assertEqual(self.codes(), ["INVALID_OR_UNREADABLE_RECEIPT"])

    def test_missing_receipt_rejected(self):
        self.receiptfile.unlink()
        self.assertEqual(self.codes(), ["INVALID_OR_UNREADABLE_RECEIPT"])


if __name__ == "__main__":
    unittest.main()
