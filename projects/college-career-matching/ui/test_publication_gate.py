"""Synthetic regression tests for the independent public-data release gate."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("publication_gate", ROOT / "publication_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

UNKNOWN = {"status": "UNKNOWN"}
VERIFIED = {"status": "VERIFIED", "source_url": "https://example.edu/official-data", "reporting_year": 2025}
COST = {**VERIFIED, "cohort_map_reference": "Synthetic cohort mapping only"}
UNITID = "123456"


def fixture():
    cost = {k: None for k in gate.BANDS}
    cost["0_30k"] = 0
    careers = {k: None for k in gate.CAREERS}
    enrollment = {k: None for k in gate.ENROLLMENT}
    evidence = {k: copy.deepcopy(UNKNOWN) for k in ("setting", "housing", "access", "aid")}
    evidence["housing"] = copy.deepcopy(VERIFIED)
    evidence["cost.0_30k"] = copy.deepcopy(COST)
    for k in gate.BANDS[1:]:
        evidence["cost." + k] = copy.deepcopy(UNKNOWN)
    for k in gate.CAREERS:
        evidence["careers." + k] = copy.deepcopy(UNKNOWN)
    for k in gate.ENROLLMENT:
        evidence["enrollment." + k] = copy.deepcopy(UNKNOWN)
    record = {
        "unitid": UNITID, "name": "Synthetic Example University", "publication_status": "APPROVED",
        "publication_approved_by_user": True, "field_provenance": evidence,
        "setting": None, "housing": False, "access": None, "aid": None,
        "cost": cost, "careers": careers, "enrollment": enrollment,
        "source": "Synthetic test fixture only", "reference_year": 2025
    }
    manifest = {"schema_version": 1, "approved_unitids": [{
        "unitid": UNITID, "approved_by": "user", "approved_on": "2026-10-09",
        "approval_reference": "SYNTHETIC TEST FIXTURE; NOT ACTUAL APPROVAL"
    }]}
    return {"schema_version": 1, "records": [record]}, manifest


class PublicationGateTests(unittest.TestCase):
    def test_synthetic_complete_fixture_passes_gate(self):
        self.assertEqual(gate.check(*fixture()), [])

    def test_empty_manifest_denies_all_records(self):
        payload, manifest = fixture()
        manifest["approved_unitids"] = []
        self.assertTrue(gate.check(payload, manifest))

    def test_unapproved_record_denied(self):
        payload, manifest = fixture()
        payload["records"][0]["publication_status"] = "DO_NOT_PUBLISH"
        self.assertTrue(gate.check(payload, manifest))

    def test_missing_explicit_user_approval_denied(self):
        payload, manifest = fixture()
        payload["records"][0]["publication_approved_by_user"] = False
        self.assertTrue(gate.check(payload, manifest))

    def test_duplicate_approval_denied(self):
        payload, manifest = fixture()
        manifest["approved_unitids"].append(copy.deepcopy(manifest["approved_unitids"][0]))
        self.assertTrue(gate.check(payload, manifest))

    def test_invalid_date_denied(self):
        payload, manifest = fixture()
        manifest["approved_unitids"][0]["approved_on"] = "2026-02-30"
        self.assertTrue(gate.check(payload, manifest))

    def test_unknown_housing_is_not_false(self):
        payload, manifest = fixture()
        r = payload["records"][0]
        r["housing"] = None
        r["field_provenance"]["housing"] = copy.deepcopy(UNKNOWN)
        self.assertEqual(gate.check(payload, manifest), [])

    def test_negative_housing_requires_verified_source(self):
        payload, manifest = fixture()
        payload["records"][0]["field_provenance"]["housing"] = copy.deepcopy(UNKNOWN)
        self.assertTrue(gate.check(payload, manifest))

    def test_zero_price_requires_cohort_reference(self):
        payload, manifest = fixture()
        del payload["records"][0]["field_provenance"]["cost.0_30k"]["cohort_map_reference"]
        self.assertTrue(gate.check(payload, manifest))

    def test_suppressed_price_has_distinct_status(self):
        payload, manifest = fixture()
        r = payload["records"][0]
        r["cost"]["0_30k"] = None
        r["field_provenance"]["cost.0_30k"] = {**VERIFIED, "status": "SUPPRESSED"}
        self.assertEqual(gate.check(payload, manifest), [])

    def test_numeric_accessibility_score_not_published(self):
        payload, manifest = fixture()
        r = payload["records"][0]
        r["access"] = 3
        r["field_provenance"]["access"] = copy.deepcopy(VERIFIED)
        self.assertTrue(gate.check(payload, manifest))

    def test_empty_aid_list_is_not_verified_none(self):
        payload, manifest = fixture()
        r = payload["records"][0]
        r["aid"] = []
        r["field_provenance"]["aid"] = copy.deepcopy(VERIFIED)
        self.assertTrue(gate.check(payload, manifest))

    def test_enrollment_missing_provenance_denied(self):
        payload, manifest = fixture()
        del payload["records"][0]["field_provenance"]["enrollment.total"]
        self.assertTrue(gate.check(payload, manifest))

    def test_negative_enrollment_denied(self):
        payload, manifest = fixture()
        r = payload["records"][0]
        r["enrollment"]["total"] = -1
        r["field_provenance"]["enrollment.total"] = copy.deepcopy(VERIFIED)
        self.assertTrue(gate.check(payload, manifest))

    def test_unverified_testing_policy_denied(self):
        payload, manifest = fixture()
        payload["records"][0]["testing_policy"] = "blind"
        self.assertTrue(gate.check(payload, manifest))

    def test_official_testing_policy_evidence_required(self):
        payload, manifest = fixture()
        r = payload["records"][0]
        r.update(testing_policy="optional", testing_policy_verified=True,
                 testing_policy_source="https://example.edu/admissions/testing", testing_policy_year=2026)
        self.assertEqual(gate.check(payload, manifest), [])

    def test_invalid_source_scheme_denied(self):
        payload, manifest = fixture()
        payload["records"][0]["field_provenance"]["housing"]["source_url"] = "http://example.edu"
        self.assertTrue(gate.check(payload, manifest))

    def test_no_public_bundle_keeps_synthetic_demo(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(gate.main(tmp), 0)

    def test_cli_rejects_unapproved_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload, manifest = fixture()
            manifest["approved_unitids"] = []
            Path(tmp, "public-data.json").write_text(json.dumps(payload))
            Path(tmp, "publication-approvals.json").write_text(json.dumps(manifest))
            self.assertEqual(gate.main(tmp), 1)


if __name__ == "__main__":
    unittest.main()
