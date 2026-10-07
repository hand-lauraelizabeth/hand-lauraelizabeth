import csv
import tempfile
import unittest
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))

from suny_transfer_program_review import build_review_queue,parse_degree,run


class SunyTransferProgramReviewTest(unittest.TestCase):
    def test_degree_parser_removes_only_detected_degree_marker(self):
        self.assertEqual(parse_degree("Business Administration A.S."),("AS","business administration"))
        self.assertEqual(parse_degree("Technology Management B.B.A."),("BBA","technology management"))
        self.assertEqual(parse_degree("Liberal Arts and Sciences"),("","liberal arts and sciences"))

    def test_review_queue_deduplicates_same_source_program_by_side_and_unitid(self):
        rows=[
            {
                "transfer_agreement_id":"SUNY-STEP-R1","source_system":"SUNY",
                "sending_unitid":"188438","sending_institution_source_id":"Adirondack",
                "sending_program_name":"Business Administration A.S.",
                "receiving_unitid":"196015","receiving_institution_source_id":"Canton",
                "receiving_program_name":"Technology Management B.B.A.",
                "source_url":"https://step.transfer.suny.edu/agreements/",
            },
            {
                "transfer_agreement_id":"SUNY-STEP-R2","source_system":"SUNY",
                "sending_unitid":"188438","sending_institution_source_id":"Adirondack",
                "sending_program_name":"Business Administration A.S.",
                "receiving_unitid":"196015","receiving_institution_source_id":"Canton",
                "receiving_program_name":"",
                "source_url":"https://step.transfer.suny.edu/agreements/",
            },
        ]
        queue,qa=build_review_queue(rows)
        self.assertEqual(qa["status"],"PASS")
        self.assertEqual(qa["review_queue_rows"],2)
        self.assertEqual(qa["receiving_agreement_rows_missing_program_text"],1)
        sending=next(r for r in queue if r["side"]=="sending")
        self.assertEqual(sending["agreement_count"],2)
        self.assertEqual(sending["parsed_degree"],"AS")
        self.assertEqual(sending["suggested_cip"],"")
        self.assertEqual(sending["reviewed_cip"],"")
        self.assertEqual(sending["review_status"],"unreviewed")

    def test_program_text_with_missing_unitid_fails(self):
        rows=[{
            "transfer_agreement_id":"SUNY-STEP-R3","source_system":"SUNY",
            "sending_unitid":"","sending_institution_source_id":"Example",
            "sending_program_name":"Business A.S.",
            "receiving_unitid":"1","receiving_institution_source_id":"Other",
            "receiving_program_name":"","source_url":"x",
        }]
        with self.assertRaises(ValueError):
            build_review_queue(rows)


if __name__=="__main__":
    unittest.main()
