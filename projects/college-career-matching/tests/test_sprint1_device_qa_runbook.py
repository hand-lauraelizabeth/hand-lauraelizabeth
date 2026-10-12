"""Assert release-test instructions include safety, coverage and honest untested state."""
import unittest
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "SPRINT1_DEVICE_QA_AND_ROLLBACK.md"


class SprintOneManualRunbook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = DOC.read_text(encoding="utf-8")

    def test_fifteen_clickthrough_cases(self):
        for i in range(1, 16):
            self.assertEqual(self.doc.count(f"| C{i:02d} |"), 1)
        for text in ("6,243", "417", "658", "138", "24 to 48", "Harvard University", "Enterprise State Community College", "Retry", "About this data"):
            self.assertIn(text, self.doc)

    def test_desktop_ios_android_not_misrepresented_as_executed(self):
        self.assertIn("Physical iOS Safari", self.doc)
        self.assertIn("Physical Android Chrome", self.doc)
        self.assertIn("Desktop Chrome/Edge", self.doc)
        self.assertGreaterEqual(self.doc.count("**NOT RUN**"), 6)
        self.assertIn("UNVERIFIED", self.doc)
        self.assertIn("NOT RELEASE-APPROVED", self.doc)

    def test_wordpress_draft_and_real_host_benchmark_guards(self):
        for text in ("1154 Draft", "1044 Draft", "452 unchanged", "3,000 ms", "median", "NOT the WordPress staging host", "zero unexpected console errors"):
            self.assertIn(text, self.doc)
        self.assertIn("Do not make the page public", self.doc)

    def test_rollback_guards(self):
        for text in ("revert commit", "Do not force-push", "NY20", "Rollback executed? NO", "NOT GRANTED", "never restore old unreviewed NY20"):
            self.assertIn(text, self.doc)


if __name__ == "__main__":
    unittest.main()
