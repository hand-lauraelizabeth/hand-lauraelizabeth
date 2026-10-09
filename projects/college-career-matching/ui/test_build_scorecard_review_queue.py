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
                writer = csv.DictWriter(handle, fieldnames=["UNITID", "INSTNM", "CONTROL", "STABBR", "LOCALE", "NPT41_PUB", "NPT41_PRIV"])
                writer.writeheader()
                writer.writerow({"UNITID": "123456", "INSTNM": "Other College", "CONTROL": "2", "STABBR": "CA", "LOCALE": "32", "NPT41_PRIV": "2000"})
                writer.writerow({"UNITID": "654321", "INSTNM": "New York College", "CONTROL": "1", "STABBR": "NY", "LOCALE": "11", "NPT41_PUB": "PS"})
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
            self.assertEqual(rows[0]["locale_category"], "City")
            self.assertEqual(rows[0]["net_price_status"], "unavailable_or_suppressed")
            self.assertEqual(rows[1]["locale_category"], "Town")
            self.assertEqual(rows[1]["net_price_status"], "reported")
            self.assertEqual(rows[0]["publication_status"], "DO_NOT_PUBLISH")
            self.assertEqual(rows[1]["net_price_population"], "PRIV")

    def test_invalid_nces_locale_remains_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.csv"
            output = Path(tmp) / "review.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["UNITID", "INSTNM", "CONTROL", "LOCALE"])
                writer.writeheader()
                for unitid, locale in [("111111", "14"), ("222222", "20"), ("333333", "43"), ("444444", "21"), ("555555", "PS")]:
                    writer.writerow({"UNITID": unitid, "INSTNM": "Synthetic " + unitid, "CONTROL": "1", "LOCALE": locale})
            self.assertEqual(queue.build(source, output, 5), 5)
            with output.open(encoding="utf-8", newline="") as handle:
                rows = {row["UNITID"]: row for row in csv.DictReader(handle)}
            self.assertEqual([rows[x]["locale_category"] for x in ("111111", "222222", "555555")], ["Unknown"] * 3)
            self.assertEqual(rows["333333"]["locale_category"], "Rural")
            self.assertEqual(rows["444444"]["locale_category"], "Suburb")
            self.assertTrue(all(row["publication_status"] == "DO_NOT_PUBLISH" for row in rows.values()))

    def test_invalid_limit_rejected(self):
        with self.assertRaisesRegex(ValueError, "LIMIT"):
            queue.build("unused.csv", "unused-output.csv", 0)


if __name__ == "__main__":
    unittest.main()
