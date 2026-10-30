"""Synthetic-only adversarial tests for independent NYC 311 receipt auditing."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlencode
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
        triples = Counter((r[5], r[3], r[6]) for r in self.rows)
        complaints = Counter(r[4] for r in self.rows)
        key_membership = hashlib.sha256()
        for key in sorted(r[0] for r in self.rows):
            encoded = key.encode("utf-8")
            key_membership.update(len(encoded).to_bytes(4, "big"))
            key_membership.update(encoded)
        triple_digest = hashlib.sha256(json.dumps(
            [[b, a, status, n] for (b, a, status), n in sorted(triples.items())],
            separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        pair_digest = hashlib.sha256(json.dumps(
            [[b, a, n] for (b, a), n in sorted(pairs.items())],
            separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        complaint_digest = hashlib.sha256(json.dumps(
            [[label, n] for label, n in sorted(complaints.items())],
            separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        predicate = "created_date >= '2026-09-01T00:00:00' AND created_date < '2026-10-01T00:00:00'"
        resource = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
        count_query = resource + "?" + urlencode({
            "$select": "count(*) as records, count(distinct unique_key) as distinct_keys",
            "$where": predicate,
        })
        aggregate_query = resource + "?" + urlencode({
            "$select": "borough,agency,count(*) as n", "$where": predicate,
            "$group": "borough,agency", "$order": "borough,agency",
            "$limit": 50000,
        })
        three_way_query = resource + "?" + urlencode({
            "$select": "borough,agency,status,count(*) as n", "$where": predicate,
            "$group": "borough,agency,status", "$order": "borough,agency,status",
            "$limit": 50000,
        })
        complaint_query = resource + "?" + urlencode({
            "$select": "complaint_type,count(*) as n", "$where": predicate,
            "$group": "complaint_type", "$order": "complaint_type",
            "$limit": 50000,
        })
        closure_query = resource + "?" + urlencode({
            "$select": "count(*) as records,count(closed_date) as populated",
            "$where": predicate,
        })
        key_query = resource + "?" + urlencode({
            "$select": "unique_key", "$where": predicate,
            "$order": "unique_key ASC",
        })
        self.receipt = {
            "where": predicate,
            "metadata_url": "https://data.cityofnewyork.us/api/views/erm2-nwe9.json",
            "count_query_url": count_query,
            "aggregate_query_url": aggregate_query,
            "three_way_aggregate_query_url": three_way_query,
            "complaint_query_url": complaint_query,
            "key_membership_query_url": key_query,
            "closure_completeness_query_url": closure_query,
            "closure_completeness_verified": True,
            "populated_closure_dates": sum(bool(r[2]) for r in self.rows),
            "missing_closure_dates": sum(not r[2] for r in self.rows),
            "complaint_distribution_verified": True,
            "key_membership_verified": True,
            "complaint_aggregate_cells": len(complaints),
            "complaint_aggregate_sha256": complaint_digest,
            "key_membership_sha256": key_membership.hexdigest(),
            "key_membership_pages": 2,
            "verified_at_utc": "2026-10-27T10:00:00+00:00",
            "dataset": "erm2-nwe9",
            "reporting_month": "2026-09",
            "publisher": "https://data.cityofnewyork.us/d/erm2-nwe9",
            "fields": list(FIELDS), "ordered_by": "unique_key ASC",
            "cross_aggregate_verified": True,
            "three_way_cross_aggregate_verified": True, "release_status": "HOLD",
            "rows": len(self.rows), "distinct_keys": len({r[0] for r in self.rows}),
            "aggregate_cells": len(pairs),
            "three_way_aggregate_cells": len(triples),
            "publisher_rows_updated_at": 1790000000,
            "page_size": 2, "pages": 2,
            "csv_sha256": hashlib.sha256(self.csvfile.read_bytes()).hexdigest(),
            "aggregate_sha256": pair_digest,
            "three_way_aggregate_sha256": triple_digest,
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


    def test_receipt_rejects_impossible_or_noninteger_page_size(self):
        for bad in (0, -1, True, 1.0, "2", 50001, None):
            with self.subTest(bad=repr(bad)):
                self.receipt["page_size"] = bad
                self.save_receipt()
                self.assertEqual(self.codes(), ["INVALID_OR_UNREADABLE_RECEIPT"])
        self.receipt["page_size"] = 2
        self.save_receipt()
        self.assertIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", self.codes())

    def test_receipt_rejects_impossible_page_count_but_allows_short_pages(self):
        for bad in (0, 1, 4, True, 2.0, "2", None):
            with self.subTest(bad=repr(bad)):
                self.receipt["pages"] = bad
                self.save_receipt()
                self.assertEqual(self.codes(), ["INVALID_OR_UNREADABLE_RECEIPT"])
        self.receipt["pages"] = 3  # Three short pages can hold three records.
        self.save_receipt()
        self.assertIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", self.codes())

    def test_query_and_month_provenance_are_bound_to_receipt(self):
        for field, bad in (
            ("where", "created_date >= '2026-08-01T00:00:00'"),
            ("metadata_url", "https://example.org/api/views/erm2-nwe9.json"),
            ("count_query_url", "https://example.org/count"),
            ("aggregate_query_url", "https://example.org/aggregate"),
            ("three_way_aggregate_query_url", "https://example.org/three"),
            ("reporting_month", "2026-08"),
        ):
            with self.subTest(field=field):
                original = self.receipt[field]
                self.receipt[field] = bad
                self.save_receipt()
                self.assertEqual(self.codes(), ["INVALID_OR_UNREADABLE_RECEIPT"])
                self.receipt[field] = original
        self.save_receipt()
        self.assertIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", self.codes())

    def test_receipt_verification_timestamp_must_be_utc(self):
        for bad in (None, "", "2026-10-27", "2026-10-27T10:00:00",
                    "2026-10-27T10:00:00-04:00", "not-a-timestamp"):
            with self.subTest(bad=bad):
                self.receipt["verified_at_utc"] = bad
                self.save_receipt()
                self.assertEqual(self.codes(), ["INVALID_OR_UNREADABLE_RECEIPT"])
        self.receipt["verified_at_utc"] = "2026-10-27T10:00:00+00:00"
        self.save_receipt()
        self.assertIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", self.codes())

    def test_receipt_rejects_spreadsheet_active_fields_even_with_recomputed_digests(self):
        """An independently forged internally consistent receipt cannot clear unsafe CSV."""
        original_rows = [row[:] for row in self.rows]
        for field_index, unsafe in (
            (3, "=1+1"),
            (4, " +SUM(1,1)"),
            (6, "@SUM(1,1)"),
            (3, "\\uff1d1+1"),
            (6, " \\u200b=1+1"),
            (3, "Safe\\u2060label"),
            (4, "Safe\\u2028label"),
            (6, "Safe\\n=1+1"),
        ):
            with self.subTest(field_index=field_index, unsafe=repr(unsafe)):
                self.rows = [row[:] for row in original_rows]
                self.rows[0][field_index] = unsafe
                self.write()  # Rebuilds receipt, CSV SHA and category digests.
                codes = self.codes()
                self.assertIn("CSV_SPREADSHEET_ACTIVE_FIELD", codes)
                self.assertNotIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", codes)
        self.rows = [row[:] for row in original_rows]
        self.write()
        self.assertIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", self.codes())

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

    def test_three_way_status_change_fails_even_if_pair_and_csv_hashes_match(self):
        # A status-only mutation preserves borough×agency and all row totals.
        original_three_way = self.receipt["three_way_aggregate_sha256"]
        self.rows[0][6] = "Closed"
        self.write()
        self.receipt["three_way_aggregate_sha256"] = original_three_way
        self.save_receipt()
        codes = self.codes()
        self.assertIn("THREE_WAY_SHA256_MISMATCH", codes)
        self.assertNotIn("AGGREGATE_SHA256_MISMATCH", codes)
        self.assertNotIn("CSV_SHA256_MISMATCH", codes)
        self.assertNotIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", codes)

    def test_three_way_receipt_contract_is_mandatory(self):
        for field, bad in (
            ("three_way_cross_aggregate_verified", False),
            ("three_way_aggregate_cells", True),
            ("three_way_aggregate_cells", 0),
            ("three_way_aggregate_sha256", "invalid"),
            ("three_way_aggregate_query_url", "https://example.org/three"),
        ):
            with self.subTest(field=field, bad=bad):
                original = self.receipt[field]
                self.receipt[field] = bad
                self.save_receipt()
                self.assertEqual(self.codes(), ["INVALID_OR_UNREADABLE_RECEIPT"])
                self.receipt[field] = original
        self.save_receipt()
        self.assertIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", self.codes())

    def test_closure_completeness_receipt_is_mandatory(self):
        for field, bad in (
            ("closure_completeness_verified", False),
            ("closure_completeness_query_url", "https://example.org/closure"),
            ("populated_closure_dates", True),
            ("populated_closure_dates", -1),
            ("missing_closure_dates", "3"),
            ("missing_closure_dates", -1),
        ):
            with self.subTest(field=field, bad=bad):
                original = self.receipt[field]
                self.receipt[field] = bad
                self.save_receipt()
                self.assertEqual(self.codes(), ["INVALID_OR_UNREADABLE_RECEIPT"])
                self.receipt[field] = original
        self.save_receipt()
        self.assertIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", self.codes())

    def test_balanced_forged_closure_receipt_fails_even_with_matching_csv_hash(self):
        # Both numbers still sum to three, but the CSV has no closed dates.
        self.receipt["populated_closure_dates"] = 1
        self.receipt["missing_closure_dates"] = 2
        self.save_receipt()
        codes = self.codes()
        self.assertIn("CLOSURE_COMPLETENESS_MISMATCH", codes)
        self.assertNotIn("CSV_SHA256_MISMATCH", codes)
        self.assertNotIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", codes)

    def test_closure_timestamp_change_detected_with_updated_csv_hash(self):
        # Other source distributions, keys, and aggregate digests are unchanged.
        self.rows[0][2] = "2026-09-01T01:00:00"
        self.write()
        self.receipt["populated_closure_dates"] = 0
        self.receipt["missing_closure_dates"] = len(self.rows)
        self.save_receipt()
        codes = self.codes()
        self.assertIn("CLOSURE_COMPLETENESS_MISMATCH", codes)
        self.assertNotIn("CSV_SHA256_MISMATCH", codes)
        self.assertNotIn("AGGREGATE_SHA256_MISMATCH", codes)

    def test_problem_distribution_detects_category_change_with_valid_other_hashes(self):
        original_complaint_digest = self.receipt["complaint_aggregate_sha256"]
        self.rows[0][4] = "Category Z"
        self.write()  # Recompute CSV, borough/agency, and status receipts.
        self.receipt["complaint_aggregate_sha256"] = original_complaint_digest
        self.save_receipt()
        codes = self.codes()
        self.assertIn("COMPLAINT_SHA256_MISMATCH", codes)
        self.assertNotIn("CSV_SHA256_MISMATCH", codes)
        self.assertNotIn("AGGREGATE_SHA256_MISMATCH", codes)
        self.assertNotIn("THREE_WAY_SHA256_MISMATCH", codes)
        self.assertNotIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", codes)

    def test_key_membership_detects_balanced_id_change(self):
        original_membership = self.receipt["key_membership_sha256"]
        self.rows[1][0] = "0002a"  # Unique and ordered, same row/cell totals.
        self.write()
        self.receipt["key_membership_sha256"] = original_membership
        self.save_receipt()
        codes = self.codes()
        self.assertIn("KEY_MEMBERSHIP_SHA256_MISMATCH", codes)
        self.assertNotIn("KEY_DUPLICATE_OR_ORDER_INVALID", codes)
        self.assertNotIn("CSV_SHA256_MISMATCH", codes)
        self.assertNotIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", codes)

    def test_new_receipt_source_contracts_are_mandatory(self):
        for field, bad in (
            ("complaint_distribution_verified", False),
            ("key_membership_verified", False),
            ("complaint_query_url", "https://example.org/problem"),
            ("key_membership_query_url", "https://example.org/keys"),
            ("complaint_aggregate_cells", 0),
            ("complaint_aggregate_sha256", "not-sha"),
            ("key_membership_sha256", "not-sha"),
            ("key_membership_pages", 0),
            ("key_membership_pages", True),
        ):
            with self.subTest(field=field, bad=bad):
                original = self.receipt[field]
                self.receipt[field] = bad
                self.save_receipt()
                self.assertEqual(self.codes(), ["INVALID_OR_UNREADABLE_RECEIPT"])
                self.receipt[field] = original
        self.save_receipt()
        self.assertIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", self.codes())

    def test_problem_cell_count_and_digest_are_both_checked(self):
        self.receipt["complaint_aggregate_cells"] += 1
        self.save_receipt()
        self.assertIn("COMPLAINT_CELL_COUNT_MISMATCH", self.codes())
        self.receipt["complaint_aggregate_cells"] -= 1
        self.receipt["complaint_aggregate_sha256"] = "0" * 64
        self.save_receipt()
        self.assertIn("COMPLAINT_SHA256_MISMATCH", self.codes())

    def test_three_way_cell_count_and_digest_detect_forgery(self):
        self.receipt["three_way_aggregate_cells"] += 1
        self.save_receipt()
        self.assertIn("THREE_WAY_CELL_COUNT_MISMATCH", self.codes())
        self.receipt["three_way_aggregate_cells"] -= 1
        self.receipt["three_way_aggregate_sha256"] = "0" * 64
        self.save_receipt()
        self.assertIn("THREE_WAY_SHA256_MISMATCH", self.codes())

    def test_duplicate_key_fails_even_if_receipt_is_recalculated(self):
        self.rows[1][0] = "0001"
        self.write()
        # Simulate a forged receipt claiming all three keys are distinct.
        self.receipt["distinct_keys"] = len(self.rows)
        self.save_receipt()
        self.assertIn("KEY_DUPLICATE_OR_ORDER_INVALID", self.codes())

    def test_out_of_month_fails_even_if_hashes_match(self):
        self.rows[2][1] = "2026-10-01T00:00:00"
        self.write()
        self.assertIn("CREATED_DATE_OUTSIDE_MONTH", self.codes())

    def test_tz_bearing_date_fails(self):
        self.rows[0][1] = "2026-09-01T00:00:00+00:00"
        self.write()
        self.assertIn("CREATED_DATE_INVALID", self.codes())

    def test_row_count_mismatch(self):
        self.receipt["rows"] = 4
        self.receipt["distinct_keys"] = 4
        self.receipt["missing_closure_dates"] = 4  # Keep new receipt arithmetic valid.
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

    def test_date_only_created_fails_even_with_matching_receipt_digests(self):
        self.rows[0][1] = "2026-09-01"
        self.write()
        self.assertIn("CREATED_DATE_INVALID", self.codes())
        self.assertNotIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", self.codes())

    def test_malformed_closed_fails_even_with_matching_receipt_digests(self):
        for value in ("2026-09-01", "2026-09-01T11:00:00+00:00",
                      "2026-02-30T11:00:00", "invalid"):
            with self.subTest(value=value):
                self.rows[0][2] = value
                self.write()
                self.assertIn("CLOSED_DATE_INVALID", self.codes())
                self.assertNotIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", self.codes())

    def test_valid_fractional_closed_and_blank_closure_pass_internal_checks(self):
        self.rows[0][2] = "2026-09-01T12:30:00.123"
        self.rows[1][2] = ""
        self.write()
        self.assertIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", self.codes())
        self.assertNotIn("CLOSED_DATE_INVALID", self.codes())



    def test_source_swap_between_digest_and_parsing_is_rejected(self):
        """A valid digest of file A must not validate parsed bytes from file B."""
        from unittest.mock import patch
        original_open = Path.open
        source_opens = 0

        def swap_on_second_open(path, mode="r", *args, **kwargs):
            nonlocal source_opens
            if Path(path) == self.csvfile:
                source_opens += 1
                if source_opens == 2:
                    # Same-length replacement preserves row count and the
                    # borough-by-agency digest; only a source-byte binding
                    # across parsing can detect this interleaving.
                    alternate = self.csvfile.with_suffix(".replacement")
                    alternate.write_bytes(self.csvfile.read_bytes().replace(
                        b"Category X", b"Category Z"))
                    alternate.replace(self.csvfile)
            return original_open(path, mode, *args, **kwargs)

        with patch.object(Path, "open", swap_on_second_open):
            codes = self.codes()
        self.assertGreaterEqual(source_opens, 2)
        self.assertIn("CSV_CHANGED_DURING_AUDIT", codes)
        self.assertNotIn("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED", codes)

if __name__ == "__main__":
    unittest.main()
