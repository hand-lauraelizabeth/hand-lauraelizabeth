"""Synthetic integration regression tests for NYC 311 disclosure."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from pipeline import ingest

FIELDS = ["unique_key","created_date","closed_date","agency","complaint_type","borough","status"]

class TestPipeline(unittest.TestCase):
    def test_aggregations_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp, out = Path(tmp)/"fixture.csv", Path(tmp)/"result.json"
            rows = [
                ["1","2026-01-10T09:00:00.000","2026-01-11T09:00:00.000","DOT","Pothole","Queens","Closed"],
                ["2","2026-01-10T09:00:00.000","","DOT","Pothole","Queens","Open"],
                ["3","2026-02-10T09:00:00.000","2026-02-09T09:00:00.000","DOT","Pothole","Queens","Closed"],
                ["4","nonsense","","DOT","Pothole","Queens","Open"],
                ["5","2026-11-01T09:00:00.000","","DOT","Pothole","Queens","Open"],
                ["6","2026-01-10T09:00:00.000","","","Noise","","Open"],
            ]
            with inp.open("w",newline="",encoding="utf-8") as f:
                w=csv.writer(f);w.writerow(FIELDS);w.writerows(rows)
            obj=ingest(inp,out,as_of="2026-10-15",min_cell=2)
            self.assertEqual(obj["quality"]["rows_read"],6)
            self.assertEqual(obj["quality"]["valid_records"],4)
            self.assertEqual(obj["quality"]["missing_or_invalid_created_date"],1)
            self.assertEqual(obj["quality"]["created_after_as_of"],1)
            self.assertEqual(obj["quality"]["closure_before_creation"],1)
            self.assertEqual(obj["quality"]["small_cells_suppressed"],2)
            self.assertEqual(obj["aggregates"][0]["requests"],2)
            self.assertNotIn("closed_with_valid_interval",obj["aggregates"][0])
            saved=json.loads(out.read_text())
            self.assertNotIn("quality",saved)
            self.assertNotIn("incident_address",out.read_text())
            self.assertEqual(saved["source_sha256"],obj["source_sha256"])
    def test_required_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp,out=Path(tmp)/"invalid.csv",Path(tmp)/"result.json"
            inp.write_text("unique_key,created_date\n1,2026-01-01\n")
            with self.assertRaisesRegex(ValueError,"Missing API columns"):
                ingest(inp,out,as_of="2026-10-15")
            self.assertFalse(out.exists())

if __name__ == "__main__":
    unittest.main()
