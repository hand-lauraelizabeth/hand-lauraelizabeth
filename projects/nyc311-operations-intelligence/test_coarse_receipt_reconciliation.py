"""Synthetic-only adversarial checks for private 311 source-to-20-cell bridge."""
import copy
from collections import Counter
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

import test_source_receipt_audit as source_tests
from coarse_receipt_reconciliation import audit, main, HOLD


class CoarseReceiptBridgeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = source_tests.ReceiptAuditTests(
            methodName="test_valid_receipt_is_still_publication_hold")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.boroughs = ("BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND")
        self.groups = ("Housing", "Transit", "Health", "Other")
        self.mapping = {f"Agency {i}": self.groups[i] for i in range(4)}
        rows = []
        for b in self.boroughs:
            for i in range(4):
                rows.extend([(f"Agency {i}", b, "Open")] * 12)
        rows.extend([("Agency 0", "UNSPECIFIED", "Closed")] * 3)
        self.fixture.rows = [
            [f"{n:06d}", "2026-09-15T12:00:00", "", a, "Synthetic", b, s]
            for n, (a, b, s) in enumerate(rows, 1)]
        self.fixture.write()
        self.fixture.receipt["page_size"] = 50
        self.fixture.receipt["pages"] = 5
        self.fixture.receipt["key_membership_pages"] = 5
        self.fixture.save_receipt()
        self.manifest_path = Path(self.fixture.tmp.name) / "coarse.json"
        pairs = Counter((b, a) for a, b, _ in rows)
        self.manifest = {
            "schema_version": "nyc311-coarse-binding-review-v1",
            "dataset_id": "erm2-nwe9", "month": "2026-09",
            "snapshot_as_of": "2026-10-27",
            "source_sha256": self.fixture.receipt["csv_sha256"],
            "group_labels": list(self.groups), "agency_to_group": self.mapping,
            "fine_rows": [{"borough": b, "agency": a, "requests": n}
                          for (b, a), n in sorted(pairs.items())],
            "coarse_cells": [{"borough": b, "group": g, "requests": 12}
                             for b in self.boroughs for g in self.groups],
            "excluded_requests": 3, "source_total_requests": len(rows),
        }
        self.save()

    def save(self):
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")

    def codes(self):
        return audit(self.fixture.csvfile, self.fixture.receiptfile,
                     self.manifest_path)

    def test_exact_20_cell_arithmetic_verified_but_publication_held(self):
        self.assertEqual(self.codes(), [
            HOLD, "PRIVATE_SOURCE_TO_20_CELL_ARITHMETIC_VERIFIED"])

    def test_balanced_fine_source_mutation_detected_even_when_totals_match(self):
        self.manifest["fine_rows"][0]["requests"] += 1
        self.manifest["fine_rows"][1]["requests"] -= 1
        self.manifest["coarse_cells"][0]["requests"] += 1
        self.manifest["coarse_cells"][1]["requests"] -= 1
        self.save()
        self.assertIn("SOURCE_AGGREGATE_DIGEST_MISMATCH", self.codes())

    def test_missing_source_group_rejected(self):
        self.manifest["fine_rows"].pop()
        self.save()
        self.assertIn("SOURCE_GROUP_COVERAGE_MISMATCH", self.codes())

    def test_month_mismatch_rejected(self):
        self.manifest["month"] = "2026-08"
        self.save()
        self.assertIn("REPORTING_MONTH_MISMATCH", self.codes())

    def test_csv_change_invalidates_receipt(self):
        self.fixture.csvfile.write_bytes(
            self.fixture.csvfile.read_bytes().replace(b"Synthetic", b"Altered"))
        self.assertIn("SOURCE_RECEIPT_AUDIT_FAILED", self.codes())

    def test_wrong_source_digest_rejected(self):
        self.manifest["source_sha256"] = "a" * 64
        self.save()
        self.assertIn("COARSE_BINDING_INVALID_OR_UNSAFE", self.codes())

    def test_coarse_cell_tamper_rejected(self):
        self.manifest["coarse_cells"][0]["requests"] += 1
        self.save()
        self.assertIn("COARSE_BINDING_INVALID_OR_UNSAFE", self.codes())

    def test_fake_zero_group_cannot_inflate_coverage(self):
        self.manifest["fine_rows"].append({
            "borough": "QUEENS", "agency": "Agency 5", "requests": 0})
        self.manifest["agency_to_group"]["Agency 5"] = "Other"
        self.save()
        self.assertIn("FINE_SOURCE_GROUP_INVALID", self.codes())

    def test_approved_receipt_fails_closed(self):
        self.fixture.receipt["release_status"] = "APPROVED"
        self.fixture.save_receipt()
        self.assertIn("SOURCE_RECEIPT_AUDIT_FAILED", self.codes())

    def test_cli_is_hold_and_does_not_print_source_values(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main([
                str(self.fixture.csvfile), str(self.fixture.receiptfile),
                str(self.manifest_path)]), 2)
        report = json.loads(output.getvalue())
        self.assertTrue(report["hold"])
        self.assertFalse(report["publication_approved"])
        for forbidden in ("Agency", "QUEENS", "UNSPECIFIED", "243"):
            self.assertNotIn(forbidden, output.getvalue())


if __name__ == "__main__":
    unittest.main()
