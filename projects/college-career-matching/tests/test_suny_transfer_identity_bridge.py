import csv
import json
import tempfile
import unittest
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from suny_transfer_identity_bridge import run


def write_csv(path, rows):
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


class SunyTransferIdentityBridgeTest(unittest.TestCase):
    def test_only_accepted_identity_populates_unitid(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            agreements = td / "agreements.csv"
            identity = td / "identity.csv"
            output = td / "out.csv"
            qa = td / "qa.json"

            write_csv(agreements, [
                {
                    "transfer_agreement_id": "A1",
                    "source_system": "SUNY",
                    "sending_institution_source_id": "SUNY Broome",
                    "receiving_institution_source_id": "SUNY Geneseo",
                    "sending_unitid": "",
                    "receiving_unitid": "",
                },
                {
                    "transfer_agreement_id": "A2",
                    "source_system": "SUNY",
                    "sending_institution_source_id": "Unresolved Campus",
                    "receiving_institution_source_id": "SUNY Geneseo",
                    "sending_unitid": "",
                    "receiving_unitid": "",
                },
            ])
            write_csv(identity, [
                {
                    "campus_name_source": "SUNY Broome",
                    "unitid": "189547",
                    "match_status": "accepted",
                    "match_method": "reviewed_alias_ny",
                },
                {
                    "campus_name_source": "SUNY Geneseo",
                    "unitid": "196167",
                    "match_status": "accepted",
                    "match_method": "reviewed_alias_ny",
                },
                {
                    "campus_name_source": "Unresolved Campus",
                    "unitid": "999999",
                    "match_status": "review",
                    "match_method": "token_signature_ny",
                },
            ])

            report = run(agreements, identity, output, qa)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["agreement_count"], 2)
            self.assertEqual(report["sending_unitid_matches"], 1)
            self.assertEqual(report["receiving_unitid_matches"], 2)
            self.assertEqual(report["both_sides_matched"], 1)

            with output.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]["sending_unitid"], "189547")
            self.assertEqual(rows[0]["receiving_unitid"], "196167")
            self.assertEqual(rows[1]["sending_unitid"], "")
            self.assertEqual(rows[1]["sending_identity_status"], "unresolved_or_review")
            self.assertEqual(rows[1]["receiving_unitid"], "196167")

            saved = json.loads(qa.read_text(encoding="utf-8"))
            self.assertEqual(saved["both_sides_match_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
