import csv
import tempfile
import unittest
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))

from suny_institution_identity import build_indexes,load_reviewed_aliases,resolve

def write_csv(path,rows):
    fields=list(rows[0])
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

class SunyReviewedIdentityRegistryTest(unittest.TestCase):
    def test_reviewed_registry_overrides_false_token_candidates(self):
        ipeds=[
            {"UNITID":"196130","INSTNM":"SUNY Buffalo State University","STABBR":"NY","CITY":"Buffalo","WEBADDR":""},
            {"UNITID":"196088","INSTNM":"University at Buffalo","STABBR":"NY","CITY":"Buffalo","WEBADDR":""},
            {"UNITID":"193946","INSTNM":"Niagara County Community College","STABBR":"NY","CITY":"Sanborn","WEBADDR":""},
            {"UNITID":"193973","INSTNM":"Niagara University","STABBR":"NY","CITY":"Niagara University","WEBADDR":""},
            {"UNITID":"193326","INSTNM":"Monroe Community College","STABBR":"NY","CITY":"Rochester","WEBADDR":""},
            {"UNITID":"193308","INSTNM":"Monroe University","STABBR":"NY","CITY":"Bronx","WEBADDR":""},
            {"UNITID":"197294","INSTNM":"SUNY Westchester Community College","STABBR":"NY","CITY":"Valhalla","WEBADDR":""},
            {"UNITID":"197285","INSTNM":"The College of Westchester","STABBR":"NY","CITY":"White Plains","WEBADDR":""},
        ]
        with tempfile.TemporaryDirectory() as td:
            reg=Path(td)/"aliases.csv"
            rows=[
                {"step_label":"Buffalo State","ipeds_name":"SUNY Buffalo State University","unitid":"196130","identity_relationship":"campus","review_status":"accepted","suny_evidence_url":"https://www.suny.edu/campuses/","reviewed_on":"2026-10-07","review_note":"reviewed"},
                {"step_label":"Niagara","ipeds_name":"Niagara County Community College","unitid":"193946","identity_relationship":"campus","review_status":"accepted","suny_evidence_url":"https://www.suny.edu/campuses/","reviewed_on":"2026-10-07","review_note":"reviewed"},
                {"step_label":"Monroe","ipeds_name":"Monroe Community College","unitid":"193326","identity_relationship":"campus","review_status":"accepted","suny_evidence_url":"https://www.suny.edu/campuses/","reviewed_on":"2026-10-07","review_note":"reviewed"},
                {"step_label":"Westchester","ipeds_name":"SUNY Westchester Community College","unitid":"197294","identity_relationship":"campus","review_status":"accepted","suny_evidence_url":"https://www.suny.edu/campuses/","reviewed_on":"2026-10-07","review_note":"reviewed"},
            ]
            write_csv(reg,rows)
            reviewed=load_reviewed_aliases(reg,ipeds)
            _,exact,token,_=build_indexes(ipeds)
            expected={"Buffalo State":"196130","Niagara":"193946","Monroe":"193326","Westchester":"197294"}
            for label,unitid in expected.items():
                got=resolve({"campus_source_id":label,"campus_name":label,"source_url":"https://step.transfer.suny.edu/agreements/"},exact,token,reviewed)
                self.assertEqual(got["unitid"],unitid)
                self.assertEqual(got["match_status"],"accepted")
                self.assertEqual(got["match_method"],"reviewed_registry_ny")

    def test_registry_must_match_current_ipeds_name(self):
        ipeds=[{"UNITID":"1","INSTNM":"Correct Institution","STABBR":"NY","CITY":"","WEBADDR":""}]
        with tempfile.TemporaryDirectory() as td:
            reg=Path(td)/"aliases.csv"
            write_csv(reg,[{"step_label":"Example","ipeds_name":"Wrong Institution","unitid":"1","identity_relationship":"campus","review_status":"accepted","suny_evidence_url":"","reviewed_on":"2026-10-07","review_note":""}])
            with self.assertRaises(ValueError):
                load_reviewed_aliases(reg,ipeds)

if __name__=="__main__":unittest.main()
