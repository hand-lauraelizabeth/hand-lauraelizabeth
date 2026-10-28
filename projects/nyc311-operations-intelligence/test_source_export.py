"""Offline adversarial tests for private NYC 311 publisher-cohort acquisition."""
import csv
from collections import Counter
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from source_export import download, month_bounds, FIELDS


def record(key):
    return {"unique_key": str(key), "created_date": "2026-09-15T09:00:00",
            "closed_date": "", "agency": "DOT", "complaint_type": "Synthetic",
            "borough": "QUEENS", "status": "Open"}


class FakePublisher:
    def __init__(self, rows=None, *, drift=None):
        self.rows = rows if rows is not None else [record("001"), record("002"), record("003")]
        self.drift = drift
        self.meta_calls = 0
        self.count_calls = 0
        self.group_calls = 0
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if "/api/views/" in url:
            self.meta_calls += 1
            fields = {
                "unique_key": "text", "created_date": "calendar_date",
                "closed_date": "calendar_date", "agency": "text",
                "complaint_type": "text", "borough": "text", "status": "text"
            }
            columns = [{"id": 100 + i, "fieldName": name, "dataTypeName": kind}
                       for i, (name, kind) in enumerate(fields.items())]
            meta = {"id": "erm2-nwe9", "provenance": "official",
                    "publicationStage": "published", "assetType": "dataset",
                    "rowIdentifierColumnId": 100, "columns": columns,
                    "rowsUpdatedAt": (123457 if self.drift == "metadata"
                                      and self.meta_calls > 1 else 123456)}
            if self.drift == "schema" and self.meta_calls > 1:
                columns.append({"id": 108, "fieldName": "new_optional_field",
                                "dataTypeName": "text"})
            if self.drift == "schema_type":
                columns[0]["dataTypeName"] = "number"
            if self.drift == "schema_duplicate":
                columns.append(dict(columns[0]))
            if self.drift == "schema_identifier":
                meta["rowIdentifierColumnId"] = 999
            if self.drift == "schema_unofficial":
                meta["provenance"] = "community"
            if self.drift == "schema_missing":
                columns.pop()
            if self.drift == "schema_bad_timestamp":
                meta["rowsUpdatedAt"] = True
            return meta
        params = parse_qs(urlparse(url).query)
        if "$group" in params:
            self.group_calls += 1
            assert params["$group"] == ["borough,agency"]
            assert "2026-09-01T00:00:00" in params["$where"][0]
            pairs = Counter((r.get("borough", ""), r.get("agency", "")) for r in self.rows)
            data = [{"borough": b, "agency": a, "n": str(n)}
                    for (b, a), n in sorted(pairs.items())]
            if self.drift in ("aggregate_mismatch", "aggregate_drift") and (
                    self.drift == "aggregate_mismatch" or self.group_calls > 1):
                data[0]["borough"] = "ALTERED SYNTHETIC BOROUGH"
            if self.drift == "aggregate_total":
                data[0]["n"] = str(int(data[0]["n"]) + 1)
            if self.drift == "aggregate_duplicate":
                data.append(dict(data[0]))
            if self.drift == "aggregate_malformed":
                del data[0]["n"]
            if self.drift == "aggregate_missing":
                return []
            return data
        if "$select" in params and "count(*)" in params["$select"][0]:
            self.count_calls += 1
            n = len(self.rows) + (1 if self.drift == "count" and self.count_calls > 1 else 0)
            return [{"records": str(n), "distinct_keys": str(n)}]
        assert params["$order"] == ["unique_key ASC"]
        assert "2026-09-01T00:00:00" in params["$where"][0]
        assert "2026-10-01T00:00:00" in params["$where"][0]
        offset, limit = int(params["$offset"][0]), int(params["$limit"][0])
        if self.drift == "truncated" and offset > 0:
            return []
        return self.rows[offset:offset + limit]


class TestSourceExport(unittest.TestCase):
    def test_month_bounds_and_invalid_months(self):
        self.assertEqual(month_bounds("2026-12"),
                         ("2026-12-01T00:00:00", "2027-01-01T00:00:00"))
        self.assertEqual(month_bounds("2028-02"),
                         ("2028-02-01T00:00:00", "2028-03-01T00:00:00"))
        for month in ("2026-13", "2026-00", "2026-9", "September", ""):
            with self.subTest(month=month), self.assertRaises(ValueError):
                month_bounds(month)

    def test_private_export_pages_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            publisher = FakePublisher()
            receipt = download("2026-09", csvfile, receiptfile, page_size=2,
                               fetch=publisher, verified_at="2026-10-26T22:00:00+00:00")
            self.assertEqual((receipt["rows"], receipt["distinct_keys"], receipt["pages"]), (3, 3, 2))
            self.assertEqual(receipt["release_status"], "HOLD")
            self.assertEqual(receipt["publisher_rows_updated_at"], 123456)
            self.assertEqual(json.loads(receiptfile.read_text()), receipt)
            with csvfile.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(list(rows[0]), list(FIELDS))
            self.assertEqual([r["unique_key"] for r in rows], ["001", "002", "003"])
            self.assertNotIn("incident_address", csvfile.read_text())
            import hashlib
            self.assertEqual(hashlib.sha256(csvfile.read_bytes()).hexdigest(), receipt["csv_sha256"])
            self.assertEqual(publisher.meta_calls, 2)
            self.assertEqual(publisher.count_calls, 2)
            self.assertEqual(publisher.group_calls, 2)
            self.assertEqual(receipt["aggregate_cells"], 1)
            self.assertEqual(len(receipt["aggregate_sha256"]), 64)
            self.assertTrue(receipt["cross_aggregate_verified"])
            self.assertIn("%24group=borough%2Cagency", receipt["aggregate_query_url"])
            self.assertNotIn("QUEENS", receiptfile.read_text())

    def test_duplicate_or_out_of_order_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            publisher = FakePublisher([record("001"), record("001"), record("003")])
            with self.assertRaisesRegex(ValueError, "Duplicate or out-of-order"):
                download("2026-09", csvfile, receiptfile, page_size=2, fetch=publisher)
            self.assertFalse(csvfile.exists())
            self.assertFalse(receiptfile.exists())

    def test_truncated_page_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            with self.assertRaisesRegex(ValueError, "Truncated"):
                download("2026-09", csvfile, receiptfile, page_size=2,
                         fetch=FakePublisher(drift="truncated"))
            self.assertFalse(csvfile.exists())
            self.assertFalse(receiptfile.exists())

    def test_source_metadata_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            with self.assertRaisesRegex(ValueError, "source changed"):
                download("2026-09", csvfile, receiptfile, page_size=2,
                         fetch=FakePublisher(drift="metadata"))
            self.assertFalse(csvfile.exists())
            self.assertFalse(receiptfile.exists())

    def test_schema_change_with_unchanged_update_clock_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            with self.assertRaisesRegex(ValueError, "source changed"):
                download("2026-09", csvfile, receiptfile, page_size=2,
                         fetch=FakePublisher(drift="schema"))
            self.assertFalse(csvfile.exists())
            self.assertFalse(receiptfile.exists())

    def test_invalid_publisher_schema_fails_before_private_export(self):
        for drift in ("schema_type", "schema_duplicate", "schema_identifier",
                      "schema_unofficial", "schema_missing"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as tmp:
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "Publisher schema"):
                    download("2026-09", csvfile, receiptfile,
                             fetch=FakePublisher(drift=drift))
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())

    def test_malformed_publisher_update_clock_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            with self.assertRaisesRegex(ValueError, "source-update timestamp"):
                download("2026-09", csvfile, receiptfile,
                         fetch=FakePublisher(drift="schema_bad_timestamp"))
            self.assertFalse(csvfile.exists())
            self.assertFalse(receiptfile.exists())

    def test_source_count_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            with self.assertRaisesRegex(ValueError, "source changed"):
                download("2026-09", csvfile, receiptfile, page_size=2,
                         fetch=FakePublisher(drift="count"))
            self.assertFalse(csvfile.exists())
            self.assertFalse(receiptfile.exists())

    def test_no_overwrite_and_no_same_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            csvfile.write_text("protected")
            with self.assertRaises(FileExistsError):
                download("2026-09", csvfile, receiptfile, fetch=FakePublisher())
            self.assertEqual(csvfile.read_text(), "protected")
            with self.assertRaisesRegex(ValueError, "must differ"):
                download("2026-09", csvfile, csvfile, fetch=FakePublisher())

    def test_reject_malformed_and_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            broken = record("001")
            del broken["unique_key"]
            with self.assertRaisesRegex(ValueError, "Missing publisher unique_key"):
                download("2026-09", csvfile, receiptfile,
                         fetch=FakePublisher([broken]))
            self.assertFalse(csvfile.exists())
            self.assertFalse(receiptfile.exists())

    def test_outside_month_and_malformed_source_timestamps_fail_closed(self):
        for created in ("2026-08-31T23:59:59", "2026-10-01T00:00:00",
                        "2026-09-15T09:00:00+00:00", "not-a-date"):
            with self.subTest(created=created), tempfile.TemporaryDirectory() as tmp:
                row = record("001")
                row["created_date"] = created
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "outside reporting month|Malformed"):
                    download("2026-09", csvfile, receiptfile,
                             fetch=FakePublisher([row]))
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())

    def test_valid_boundary_timestamps(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [record("001"), record("002")]
            rows[0]["created_date"] = "2026-09-01T00:00:00.000"
            rows[1]["created_date"] = "2026-09-30T23:59:59.999"
            receipt = download("2026-09", Path(tmp)/"source.csv",
                               Path(tmp)/"receipt.json", fetch=FakePublisher(rows))
            self.assertEqual(receipt["rows"], 2)

    def test_aggregate_mismatch_or_drift_fails_closed(self):
        for drift in ("aggregate_mismatch", "aggregate_drift"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as tmp:
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "aggregates changed|cross-aggregate"):
                    download("2026-09", csvfile, receiptfile,
                             fetch=FakePublisher(drift=drift), page_size=2)
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())

    def test_invalid_official_aggregates_fail_closed(self):
        for drift in ("aggregate_total", "aggregate_duplicate",
                      "aggregate_malformed", "aggregate_missing"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as tmp:
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "aggregate"):
                    download("2026-09", csvfile, receiptfile,
                             fetch=FakePublisher(drift=drift))
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())

    def test_source_aggregate_matches_multiple_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [record("001"), record("002"), record("003")]
            rows[1]["borough"] = "BROOKLYN"
            rows[2]["agency"] = "DEP"
            receipt = download("2026-09", Path(tmp)/"source.csv",
                               Path(tmp)/"receipt.json", fetch=FakePublisher(rows),
                               page_size=2)
            self.assertEqual(receipt["aggregate_cells"], 3)
            self.assertEqual(receipt["rows"], 3)

    def test_late_csv_collision_never_overwrites_other_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            original_link = os.link
            def race(src, dst):
                if Path(dst) == csvfile:
                    csvfile.write_text("protected concurrent CSV", encoding="utf-8")
                return original_link(src, dst)
            with patch("source_export.os.link", side_effect=race):
                with self.assertRaises(FileExistsError):
                    download("2026-09", csvfile, receiptfile, fetch=FakePublisher())
            self.assertEqual(csvfile.read_text(encoding="utf-8"), "protected concurrent CSV")
            self.assertFalse(receiptfile.exists())
            self.assertEqual(list(Path(tmp).glob(".nyc311-*")), [])

    def test_late_receipt_collision_preserves_receipt_and_rolls_back_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            original_link = os.link
            def race(src, dst):
                if Path(dst) == receiptfile:
                    receiptfile.write_text("protected concurrent receipt", encoding="utf-8")
                return original_link(src, dst)
            with patch("source_export.os.link", side_effect=race):
                with self.assertRaises(FileExistsError):
                    download("2026-09", csvfile, receiptfile, fetch=FakePublisher())
            self.assertFalse(csvfile.exists())
            self.assertEqual(receiptfile.read_text(encoding="utf-8"), "protected concurrent receipt")
            self.assertEqual(list(Path(tmp).glob(".nyc311-*")), [])


    def test_reject_coerced_publisher_cohort_counts(self):
        # Prior int(value) silently accepted True, 1.0 and padded strings.
        for field in ("records", "distinct_keys"):
            for bad in (True, 1.0, " 1 ", "1.0", None, [], {"n": 1}):
                with self.subTest(field=field, bad=repr(bad)), tempfile.TemporaryDirectory() as tmp:
                    publisher = FakePublisher([record("001")])
                    def malformed(url):
                        result = publisher(url)
                        params = parse_qs(urlparse(url).query)
                        if "$select" in params and "count(*)" in params["$select"][0]:
                            result[0][field] = bad
                        return result
                    csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                    with self.assertRaisesRegex(ValueError, "Invalid publisher count"):
                        download("2026-09", csvfile, receiptfile, fetch=malformed)
                    self.assertFalse(csvfile.exists())
                    self.assertFalse(receiptfile.exists())

    def test_reject_noncanonical_official_aggregate_counts(self):
        for bad in (True, 1.0, " 1 ", "1.0", None, [], {"n": 1}):
            with self.subTest(bad=repr(bad)), tempfile.TemporaryDirectory() as tmp:
                publisher = FakePublisher([record("001")])
                def malformed(url):
                    result = publisher(url)
                    if "$group" in parse_qs(urlparse(url).query):
                        result[0]["n"] = bad
                    return result
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "Invalid official aggregate count"):
                    download("2026-09", csvfile, receiptfile, fetch=malformed)
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())

    def test_page_size_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n in (0, 50001, -1, True, 1.5):
                with self.subTest(n=n), self.assertRaises(ValueError):
                    download("2026-09", Path(tmp)/"x.csv", Path(tmp)/"r.json",
                             page_size=n, fetch=FakePublisher())

    def test_reject_date_only_and_partial_created_timestamps(self):
        for value in ("2026-09-15", "2026-09-15T09:00", "2026-09-15 09:00:00"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                row = record("001")
                row["created_date"] = value
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "Malformed publisher floating timestamp"):
                    download("2026-09", csvfile, receiptfile, fetch=FakePublisher([row]))
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())

    def test_reject_invalid_optional_closed_timestamps(self):
        for value in ("2026-09-15", "2026-09-15T09:00:00Z",
                      "2026-02-30T09:00:00", "not-a-date"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                row = record("001")
                row["closed_date"] = value
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "Malformed publisher floating timestamp"):
                    download("2026-09", csvfile, receiptfile, fetch=FakePublisher([row]))
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())

    def test_optional_null_or_omitted_closure_normalized_to_blank(self):
        for kind in ("null", "omitted"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                row = record("001")
                if kind == "null":
                    row["closed_date"] = None
                else:
                    del row["closed_date"]
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                receipt = download("2026-09", csvfile, receiptfile, fetch=FakePublisher([row]))
                self.assertEqual(receipt["rows"], 1)
                with csvfile.open(newline="", encoding="utf-8") as stream:
                    self.assertEqual(list(csv.DictReader(stream))[0]["closed_date"], "")

    def test_valid_fractional_closed_timestamp_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = record("001")
            row["closed_date"] = "2026-09-15T10:01:02.123"
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            download("2026-09", csvfile, receiptfile, fetch=FakePublisher([row]))
            with csvfile.open(newline="", encoding="utf-8") as stream:
                self.assertEqual(list(csv.DictReader(stream))[0]["closed_date"],
                                 "2026-09-15T10:01:02.123")


if __name__ == "__main__":
    unittest.main()
