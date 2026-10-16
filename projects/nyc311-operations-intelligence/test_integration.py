"""Synthetic end-to-end disclosure test; not real NYC source evidence."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from pipeline import ingest

FIELDS=["unique_key","created_date","closed_date","agency","complaint_type","borough","status"]
class IntegrationTests(unittest.TestCase):
    def test_end_to_end_suppression_and_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            src,out=Path(tmp)/"input.csv",Path(tmp)/"output.json"
            with src.open("w",newline="",encoding="utf-8") as f:
                writer=csv.writer(f);writer.writerow(FIELDS)
                for i in range(25):
                    writer.writerow([str(i),"2026-09-01T12:00:00","2026-09-02T12:00:00" if i < 19 else "","DOT","Road","Queens","Closed" if i < 19 else "Open"])
                for i in range(3):
                    writer.writerow([str(100+i),"2026-09-01T12:00:00","","DOT","Noise","Queens","Open"])
            obj=ingest(src,out,as_of="2026-10-15",min_cell=10)
            saved=json.loads(out.read_text())
            self.assertEqual(len(saved["aggregates"]),1)
            self.assertEqual(saved["aggregates"][0]["requests"],25)
            self.assertNotIn("closed_with_valid_interval",saved["aggregates"][0])
            self.assertEqual(obj["quality"]["small_cells_suppressed"],1)
            self.assertNotIn("quality",saved)
            self.assertNotIn("small_cells_suppressed",out.read_text())
            self.assertFalse(saved["disclosure"]["marginals_available"])

if __name__=="__main__":
    unittest.main()
