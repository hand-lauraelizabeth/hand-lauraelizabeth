"""Synthetic regression coverage for public-explorer publication containment."""
import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "publication_exposure_audit.py"
spec = importlib.util.spec_from_file_location("publication_exposure_audit", MODULE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PublicationExposureAuditTests(unittest.TestCase):
    def test_synthetic_only_document_passes(self):
        html = '<div id="leh-ccx"><p>Fictional program demo</p></div><script>const mode="fixture";</script>'
        self.assertEqual(audit.inspect_public_explorer(html), [])

    def test_embedded_real_institutions_blocked(self):
        html = '<script type="application/json" id="ny20-embedded-data">{"institutions":[{"unitid":"123456"}]}</script>'
        self.assertIn("unapproved institution data embedded in public HTML", audit.inspect_public_explorer(html))

    def test_external_national_loader_blocked(self):
        html = '<script>const SOURCE_URL="https://example.edu/national/manifest.v1.json";</script>'
        self.assertIn("national institution-data loader in public HTML", audit.inspect_public_explorer(html))

    def test_real_institution_panel_blocked(self):
        self.assertIn("real-institution UI is present", audit.inspect_public_explorer('<section id="ccx-real-institutions"></section>'))

    def test_unrelated_public_program_service_remains_allowed(self):
        html = '<script type="module">import {MatchingServiceClient} from "./prototype/client.js";</script>'
        self.assertEqual(audit.inspect_public_explorer(html), [])


if __name__ == "__main__":
    unittest.main()
