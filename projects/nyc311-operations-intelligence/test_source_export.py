"""Offline adversarial tests for private NYC 311 publisher-cohort acquisition."""
import csv
import json
import tempfile
import unittest
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
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if "/api/views/" in url:
            self.meta_calls += 1
            return {"rowsUpdatedAt": 123456 if not (self.drift == "metadata" and self.meta_calls > 1) else 123457}
        params = parse_qs(urlparse(url).query)
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

    def test_page_size_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n in (0, 50001, -1, True, 1.5):
                with self.subTest(n=n), self.assertRaises(ValueError):
                    download("2026-09", Path(tmp)/"x.csv", Path(tmp)/"r.json",
                             page_size=n, fetch=FakePublisher())


if __name__ == "__main__":
    unittest.main()
