"""Synthetic tests for private Scorecard evidence queue."""
import csv
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("review_queue", Path(__file__).with_name("build_scorecard_review_queue.py"))
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)


class ReviewQueueTests(unittest.TestCase):
    def test_zip_ignores_macos_metadata_and_prioritizes_ny(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "sample.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["UNITID", "INSTNM", "CONTROL", "STABBR", "NPT41_PUB", "NPT41_PRIV"])
                writer.writeheader()
                writer.writerow({"UNITID": "123456", "INSTNM": "Other College", "CONTROL": "2", "STABBR": "CA", "NPT41_PRIV": "2000"})
                writer.writerow({"UNITID": "654321", "INSTNM": "New York College", "CONTROL": "1", "STABBR": "NY", "NPT41_PUB": "PS"})
            archive = root / "source.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.write(csv_path, arcname="institutions.csv")
                handle.writestr("__MACOSX/._institutions.csv", b"resource")
            output = root / "queue.csv"
            self.assertEqual(queue.build(archive, output, 2), 2)
            with output.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["UNITID"], "654321")
            self.assertEqual(rows[0]["net_price_sample"], "PS")
            self.assertEqual(rows[0]["publication_status"], "DO_NOT_PUBLISH")
            self.assertEqual(rows[1]["net_price_population"], "PRIV")

    def test_invalid_limit_rejected(self):
        with self.assertRaisesRegex(ValueError, "LIMIT"):
            queue.build("unused.csv", "unused-output.csv", 0)


if __name__ == "__main__":
    unittest.main()
