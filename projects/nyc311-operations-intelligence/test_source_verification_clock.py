"""Synthetic regression: a private source receipt must timestamp *completed* checks.

No real NYC 311 records, identifiers or source CSVs are included.
"""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from source_export import download
from source_receipt_audit import audit
from test_source_export import FakePublisher


class VerificationClockTests(unittest.TestCase):
    def paths(self, tmp):
        return Path(tmp) / "private.csv", Path(tmp) / "private-receipt.json"

    def test_verification_time_follows_final_publisher_check(self):
        publisher = FakePublisher()
        observed_last_check = []
        def fetch(url):
            response = publisher(url)
            if "$group" in parse_qs(urlparse(url).query) and publisher.group_calls == 2:
                observed_last_check.append(dt.datetime.now(dt.timezone.utc))
            return response
        with tempfile.TemporaryDirectory() as tmp:
            csv_path, receipt_path = self.paths(tmp)
            receipt = download("2026-09", csv_path, receipt_path, fetch=fetch, page_size=2)
            self.assertEqual(len(observed_last_check), 1)
            verified = dt.datetime.fromisoformat(receipt["verified_at_utc"])
            self.assertGreaterEqual(verified, observed_last_check[0],
                                    "receipt must describe completion, not acquisition start")
            self.assertEqual(receipt["release_status"], "HOLD")

    def test_invalid_override_fails_before_publishing(self):
        for value in ("not-a-timestamp", "2026-10-27T08:00:00",
                      "2026-10-27T08:00:00-04:00", "2099-01-01T00:00:00+00:00"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                csv_path, receipt_path = self.paths(tmp)
                with self.assertRaises(ValueError):
                    download("2026-09", csv_path, receipt_path,
                             fetch=FakePublisher(), verified_at=value)
                self.assertFalse(csv_path.exists())
                self.assertFalse(receipt_path.exists())

    def test_publisher_update_after_verification_is_rejected_by_exporter(self):
        publisher = FakePublisher()
        def future_metadata(url):
            data = publisher(url)
            if "/api/views/" in url:
                data["rowsUpdatedAt"] = 4102444800  # 2100-01-01 UTC, synthetic
            return data
        with tempfile.TemporaryDirectory() as tmp:
            csv_path, receipt_path = self.paths(tmp)
            with self.assertRaises(ValueError):
                download("2026-09", csv_path, receipt_path, fetch=future_metadata)
            self.assertFalse(csv_path.exists())
            self.assertFalse(receipt_path.exists())

    def test_independent_auditor_rejects_impossible_publisher_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path, receipt_path = self.paths(tmp)
            download("2026-09", csv_path, receipt_path, fetch=FakePublisher())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["publisher_rows_updated_at"] = 4102444800
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertEqual(audit(csv_path, receipt_path),
                             ["INVALID_OR_UNREADABLE_RECEIPT"])


if __name__ == "__main__":
    unittest.main()
