import csv
import tempfile
import unittest
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from suny_transfer_agreement_adapter import run

class SunyTransferAgreementAdapterTest(unittest.TestCase):
    def test_live_page_columns_preserve_direction_and_destination(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);src=td/"step.csv";out=td/"out.csv";qa=td/"qa.json"
            with src.open("w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f,fieldnames=["ID","Initial Campus","Partner Campus","Type","Program","Destination","Source"])
                w.writeheader();w.writerow({
                    "ID":"R284","Initial Campus":"Adirondack","Partner Campus":"Canton",
                    "Type":"Articulation Agreement","Program":"Business Administration A.S.",
                    "Destination":"Technology Management B.B.A.","Source":"Business Administration A.S."
                })
            report=run(src,out,qa,retrieved_at="2026-10-07T00:00:00+00:00")
            self.assertEqual(report["status"],"PASS")
            with out.open(newline="",encoding="utf-8") as f: row=next(csv.DictReader(f))
            self.assertEqual(row["transfer_agreement_id"],"SUNY-STEP-R284")
            self.assertEqual(row["sending_institution_source_id"],"Adirondack")
            self.assertEqual(row["receiving_institution_source_id"],"Canton")
            self.assertEqual(row["sending_program_name"],"Business Administration A.S.")
            self.assertEqual(row["receiving_program_name"],"Technology Management B.B.A.")
            self.assertEqual(row["sending_unitid"],"")
            self.assertEqual(row["receiving_unitid"],"")

if __name__=="__main__": unittest.main()
