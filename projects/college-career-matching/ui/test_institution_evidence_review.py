"""Synthetic regression tests for evidence-review status audit."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("evidence_review", Path(__file__).with_name("institution_evidence_review.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class EvidenceAuditTests(unittest.TestCase):
    def audit_rows(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.csv"
            columns = ["UNITID", "INSTNM", "publication_status", "institution_identity_source",
                       "locale_evidence_source", "housing_evidence_source", "aid_evidence_source",
                       "accessibility_evidence_source", "cohort_dictionary_source", "net_price_cohort_year"]
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns)
                writer.writeheader()
                writer.writerows(rows)
            return mod.audit(path)

    def test_unreviewed_is_blocked(self):
        errors, counts = self.audit_rows([{"UNITID": "123456", "publication_status": "DO_NOT_PUBLISH"}])
        self.assertEqual(errors, [])
        self.assertEqual(counts["blocked"], 1)

    def test_approved_without_evidence_is_rejected(self):
        errors, _ = self.audit_rows([{"UNITID": "123456", "publication_status": "APPROVED"}])
        self.assertTrue(any("lacks cohort_dictionary_source" in error for error in errors))

    def test_invalid_identifier_rejected(self):
        errors, _ = self.audit_rows([{"UNITID": "12345678", "publication_status": "DO_NOT_PUBLISH"}])
        self.assertTrue(any("six-digit" in error for error in errors))

    def test_unrecognized_status_rejected(self):
        errors, _ = self.audit_rows([{"unitid": "123456", "publication_status": "MAYBE"}])
        self.assertTrue(any("unknown publication_status" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
