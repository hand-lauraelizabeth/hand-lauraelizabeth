"""Synthetic-only smoke tests for the private NYC 311 release gate."""
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import unittest

from test_reconcile_csv import fixture, rows
from release_gate import verify_release
from reconcile_csv import COLUMNS
from validate_snapshot import DATASET, ENDPOINT


class GateSmoke(unittest.TestCase):
    def test_gate_checks_synthetic_export(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "sample.csv"
            csv_path.write_text(rows())
            manifest = {
                "dataset_id": DATASET, "source_endpoint": ENDPOINT, "month": "2026-09",
                "where": "created_date >= '2026-09-01T00:00:00' AND created_date < '2026-10-01T00:00:00'",
                "selected_fields": list(COLUMNS),
                "paging": "unique_key ASC (strict numeric-text key ordering)",
                "page_size": 5000, "source_count_before": 30,
                "source_count_after": 30, "rows_exported": 30,
                "source_bytes": csv_path.stat().st_size,
                "sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
                "retrieved_utc": datetime(2026, 10, 17, tzinfo=timezone.utc).isoformat(),
                "null_or_omitted_optional_fields": {},
            }
            result = verify_release(csv_path, manifest, fixture())
            self.assertEqual(result["records"], 30)
            self.assertFalse(result["public_release_approved"])


if __name__ == "__main__":
    unittest.main()
