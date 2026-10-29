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

from source_export import download, month_bounds, FIELDS, parse_floating_timestamp


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
        self.three_calls = 0
        self.closure_calls = 0
        self.status_closure_calls = 0
        self.chronology_calls = 0
        self.chronology_status_calls = 0
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
        if (params.get("$group") == ["status"]
                and params.get("$select") == ["status,count(*) as n"]):
            self.chronology_status_calls += 1
            where = params["$where"][0]
            reverse = "closed_date < created_date" in where
            equal = "closed_date = created_date" in where
            assert reverse or equal
            counts = Counter()
            for row in self.rows:
                if not row.get("closed_date"):
                    continue
                try:
                    created = parse_floating_timestamp(row["created_date"], required=True)
                    closed = parse_floating_timestamp(row["closed_date"], required=True)
                except ValueError:
                    continue
                if (reverse and closed < created) or (equal and closed == created):
                    counts[row.get("status", "")] += 1
            if (reverse and self.drift in ("chronology_status_drift",
                                          "chronology_status_local_mismatch")
                    and (self.drift == "chronology_status_local_mismatch"
                         or self.chronology_status_calls > 2)):
                counts["Closed"] -= 1
                counts["Pending"] += 1
            data = [{"status": status, "n": str(n)}
                    for status, n in sorted(counts.items()) if n > 0]
            if self.drift == "chronology_status_duplicate" and data:
                data.append(dict(data[0]))
            if self.drift == "chronology_status_malformed" and data:
                data[0]["n"] = True
            if self.drift == "chronology_status_unknown" and data:
                data[0]["status"] = "UNKNOWN SYNTHETIC STATUS"
            if self.drift == "chronology_status_overpopulated" and data:
                data[0]["n"] = str(len(self.rows) + 1)
            return data
        if "$group" in params and params["$group"] == ["status"]:
            self.status_closure_calls += 1
            counts = Counter(r.get("status", "") for r in self.rows)
            populated = Counter(r.get("status", "") for r in self.rows
                                if r.get("closed_date"))
            statuses = sorted(counts)
            if self.drift == "closure_local_mismatch":
                # Keep independent publisher aggregates internally consistent;
                # the downloaded rows alone should trigger the original gate.
                populated[statuses[0]] += 1
            if self.drift in ("status_closure_drift", "status_closure_local_mismatch"):
                if (self.drift == "status_closure_local_mismatch"
                        or self.status_closure_calls > 1):
                    # Swap closure presence across statuses, preserving all totals.
                    populated[statuses[0]] -= 1
                    populated[statuses[1]] += 1
            data = [{"status": s, "records": str(counts[s]),
                     "populated": str(populated[s])} for s in statuses]
            if self.drift == "status_closure_duplicate":
                data.append(dict(data[0]))
            if self.drift == "status_closure_malformed":
                data[0]["populated"] = True
            if self.drift == "status_closure_total":
                data[0]["records"] = str(counts[statuses[0]] + 1)
            if self.drift == "status_closure_overpopulated":
                data[0]["populated"] = str(counts[statuses[0]] + 1)
            if self.drift == "status_closure_empty":
                return []
            return data
        if "$group" in params and params["$group"] == ["borough,agency,status"]:
            self.three_calls += 1
            counts = Counter((r.get("borough", ""), r.get("agency", ""),
                              r.get("status", "")) for r in self.rows)
            if self.drift in ("three_balanced", "three_drift") and (
                    self.drift == "three_balanced" or self.three_calls > 1):
                first, second = sorted(counts)
                counts[first] += 1
                counts[second] -= 1
            data = [{"borough": b, "agency": a, "status": status, "n": str(n)}
                    for (b, a, status), n in sorted(counts.items()) if n > 0]
            if self.drift == "three_pair_mismatch":
                data[0]["borough"] = "SYNTHETIC OTHER BOROUGH"
            if self.drift == "three_duplicate":
                data.append(dict(data[0]))
            if self.drift == "three_total":
                data[0]["n"] = str(int(data[0]["n"]) + 1)
            if self.drift == "three_malformed":
                data[0]["n"] = True
            return data
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
        if params.get("$select") == ["count(*) as n"]:
            self.chronology_calls += 1
            where = params["$where"][0]
            reverse = "closed_date < created_date" in where
            equal = "closed_date = created_date" in where
            assert reverse or equal
            n = 0
            for row in self.rows:
                closed = row.get("closed_date")
                if not closed:
                    continue
                # A fake publisher's aggregate must not preempt the exporter's
                # separate malformed-row validation with a datetime exception.
                try:
                    created_dt = parse_floating_timestamp(row["created_date"], required=True)
                    closed_dt = parse_floating_timestamp(closed, required=True)
                except ValueError:
                    continue
                if (reverse and closed_dt < created_dt) or (equal and closed_dt == created_dt):
                    n += 1
            if reverse and self.drift == "chronology_drift" and self.chronology_calls > 2:
                n += 1
            if reverse and self.drift == "chronology_local_mismatch":
                n += 1
            if self.drift == "chronology_malformed":
                return [{"n": True}]
            if self.drift == "chronology_overpopulated":
                return [{"n": len(self.rows) + 1}]
            return [{"n": str(n)}]
        if "$select" in params and "count(closed_date)" in params["$select"][0]:
            self.closure_calls += 1
            populated = sum(bool(r.get("closed_date")) for r in self.rows)
            if self.drift == "closure_drift" and self.closure_calls > 1:
                populated += 1
            if self.drift == "closure_local_mismatch":
                populated += 1
            if self.drift == "closure_malformed":
                return [{"records": str(len(self.rows)), "populated": True}]
            if self.drift == "closure_total":
                return [{"records": str(len(self.rows) + 1), "populated": str(populated)}]
            return [{"records": str(len(self.rows)), "populated": str(populated)}]
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
            self.assertEqual(publisher.three_calls, 2)
            self.assertEqual(publisher.status_closure_calls, 2)
            self.assertTrue(receipt["three_way_cross_aggregate_verified"])
            self.assertEqual(receipt["three_way_aggregate_cells"], 1)
            self.assertEqual(len(receipt["three_way_aggregate_sha256"]), 64)
            self.assertNotIn("Open", receiptfile.read_text())
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

    def test_three_way_balanced_status_change_and_drift_fail_closed(self):
        # Two-way borough/agency and total counts remain identical throughout.
        rows = [record(f"{i:03d}") for i in range(1, 5)]
        rows[0]["status"] = rows[1]["status"] = "Closed"
        for drift in ("three_balanced", "three_drift"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as tmp:
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "three-way"):
                    download("2026-09", csvfile, receiptfile,
                             fetch=FakePublisher(rows, drift=drift), page_size=2)
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())

    def test_three_way_cross_pair_disagreement_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            with self.assertRaisesRegex(ValueError, "three-way and two-way"):
                download("2026-09", csvfile, receiptfile,
                         fetch=FakePublisher(drift="three_pair_mismatch"))
            self.assertFalse(csvfile.exists())
            self.assertFalse(receiptfile.exists())

    def test_malformed_duplicate_or_inconsistent_three_way_fails_closed(self):
        for drift in ("three_duplicate", "three_total", "three_malformed"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as tmp:
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "three-way"):
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

    def test_closure_completeness_reconciles_local_and_publisher(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [record("001"), record("002"), record("003")]
            rows[0]["closed_date"] = "2026-09-16T10:05:00"
            publisher = FakePublisher(rows=rows)
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            receipt = download("2026-09", csvfile, receiptfile, fetch=publisher,
                               verified_at="2026-10-29T12:00:00+00:00")
            self.assertEqual(receipt["populated_closure_dates"], 1)
            self.assertEqual(receipt["missing_closure_dates"], 2)
            self.assertTrue(receipt["closure_completeness_verified"])
            self.assertEqual(publisher.closure_calls, 2)
            self.assertIn("count%28closed_date%29", receipt["closure_completeness_query_url"])

    def test_closure_only_drift_and_mismatch_fail_closed(self):
        for drift in ("closure_drift", "closure_local_mismatch",
                      "closure_malformed", "closure_total"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as tmp:
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "closure completeness"):
                    download("2026-09", csvfile, receiptfile, fetch=FakePublisher(drift=drift),
                             verified_at="2026-10-29T12:00:00+00:00")
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())

    def test_status_closure_cross_tab_reconciles_and_receipt_is_aggregate_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [record("001"), record("002"), record("003")]
            rows[0]["status"] = "Closed"
            rows[0]["closed_date"] = "2026-09-16T10:05:00"
            rows[1]["closed_date"] = "2026-09-16T11:05:00"  # Open with timestamp
            publisher = FakePublisher(rows=rows)
            csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
            receipt = download("2026-09", csvfile, receiptfile, fetch=publisher)
            self.assertEqual((receipt["rows"], receipt["populated_closure_dates"]), (3, 2))
            self.assertEqual(receipt["status_closure_aggregate_cells"], 2)
            self.assertEqual(publisher.status_closure_calls, 2)
            self.assertTrue(receipt["status_closure_cross_aggregate_verified"])
            self.assertEqual(len(receipt["status_closure_aggregate_sha256"]), 64)
            self.assertNotIn("status_closure_counts", receipt)
            self.assertIn("%24group=status", receipt["status_closure_query_url"])

    def test_status_closure_same_total_swap_and_invalid_cells_fail_closed(self):
        for drift in ("status_closure_drift", "status_closure_local_mismatch",
                      "status_closure_duplicate", "status_closure_malformed",
                      "status_closure_total", "status_closure_overpopulated",
                      "status_closure_empty"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as tmp:
                rows = [record("001"), record("002"), record("003")]
                rows[0]["status"] = "Closed"
                rows[0]["closed_date"] = "2026-09-16T10:05:00"
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "status-closure"):
                    download("2026-09", csvfile, receiptfile,
                             fetch=FakePublisher(rows=rows, drift=drift))
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())


    def test_closure_chronology_partition_and_aggregate_only_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [record(f"{i:03d}") for i in range(1, 5)]
            rows[0]["status"] = "Closed"
            rows[0]["closed_date"] = "2026-09-15T08:59:59"  # reversed, same day
            rows[1]["status"] = "Pending"
            rows[1]["closed_date"] = "2026-09-15T09:00:00"  # equal, not negative
            rows[2]["closed_date"] = "2026-09-16T09:00:00"  # positive, Open
            publisher = FakePublisher(rows)
            receipt = download("2026-09", Path(tmp)/"source.csv",
                               Path(tmp)/"receipt.json", fetch=publisher)
            self.assertEqual((receipt["reversed_closure_dates"],
                              receipt["equal_closure_dates"],
                              receipt["nonnegative_closure_dates"],
                              receipt["positive_closure_dates"]), (1, 1, 2, 1))
            self.assertEqual(publisher.chronology_calls, 4)
            self.assertTrue(receipt["closure_chronology_verified"])
            self.assertIn("closed_date+%3C+created_date", receipt["reversed_closure_query_url"])
            self.assertIn("closed_date+%3D+created_date", receipt["equal_closure_query_url"])
            self.assertNotIn("unique_key", str({k: v for k, v in receipt.items()
                                                 if k.startswith("reversed_closure")}))

    def test_closure_chronology_drift_and_local_mismatch_fail_closed(self):
        for drift in ("chronology_drift", "chronology_local_mismatch",
                      "chronology_malformed", "chronology_overpopulated"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as tmp:
                row = record("001")
                row["closed_date"] = "2026-09-16T09:00:00"
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "closure chronology"):
                    download("2026-09", csvfile, receiptfile,
                             fetch=FakePublisher([row], drift=drift))
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())

    def test_status_chronology_cross_tab_and_private_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [record(f"{i:03d}") for i in range(1, 6)]
            for i in (0, 1):
                rows[i]["status"] = "Closed"
                rows[i]["closed_date"] = "2026-09-15T08:59:59"
            rows[2]["status"] = "Pending"
            rows[2]["closed_date"] = "2026-09-15T08:59:59"
            rows[3]["status"] = "Pending"
            rows[3]["closed_date"] = "2026-09-15T09:00:00"
            publisher = FakePublisher(rows)
            receipt = download("2026-09", Path(tmp)/"source.csv",
                               Path(tmp)/"receipt.json", fetch=publisher)
            self.assertEqual((receipt["reversed_closure_dates"],
                              receipt["equal_closure_dates"]), (3, 1))
            self.assertEqual(publisher.chronology_status_calls, 4)
            self.assertTrue(receipt["status_chronology_verified"])
            self.assertEqual(len(receipt["status_chronology_sha256"]), 64)
            self.assertNotIn("status_chronology_counts", receipt)
            self.assertIn("%24group=status", receipt["status_chronology_query_urls"]["reversed"])
            self.assertNotIn("Closed", Path(tmp, "receipt.json").read_text())
            self.assertNotIn("Pending", Path(tmp, "receipt.json").read_text())

    def test_status_chronology_balanced_swaps_and_bad_cells_fail_closed(self):
        for drift in ("chronology_status_drift", "chronology_status_local_mismatch",
                      "chronology_status_duplicate", "chronology_status_malformed",
                      "chronology_status_unknown", "chronology_status_overpopulated"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as tmp:
                rows = [record(f"{i:03d}") for i in range(1, 6)]
                for i in (0, 1):
                    rows[i]["status"] = "Closed"
                    rows[i]["closed_date"] = "2026-09-15T08:59:59"
                rows[2]["status"] = "Pending"
                rows[2]["closed_date"] = "2026-09-15T08:59:59"
                rows[3]["status"] = "Pending"
                rows[3]["closed_date"] = "2026-09-15T09:00:00"
                csvfile, receiptfile = Path(tmp)/"source.csv", Path(tmp)/"receipt.json"
                with self.assertRaisesRegex(ValueError, "status-chronology"):
                    download("2026-09", csvfile, receiptfile,
                             fetch=FakePublisher(rows, drift=drift))
                self.assertFalse(csvfile.exists())
                self.assertFalse(receiptfile.exists())


if __name__ == "__main__":
    unittest.main()
