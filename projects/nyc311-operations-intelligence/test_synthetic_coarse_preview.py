"""No-dependency contract checks for the HOLD-only 311 synthetic preview."""
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

PATH = Path(__file__).with_name("synthetic_coarse_preview.html")
BOROUGHS = {"Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"}
GROUPS = {"Group A", "Group B", "Group C", "Group D"}

class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

class SyntheticPreviewContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PATH.read_text(encoding="utf-8")
        cls.parser = Tags()
        cls.parser.feed(cls.html)
        match = re.search(r'<script id="synthetic-cells" type="application/json">(.*?)</script>', cls.html, re.S)
        assert match, "synthetic fixture missing"
        cls.rows = json.loads(match.group(1))

    def test_exactly_twenty_complete_synthetic_cells(self):
        self.assertEqual(len(self.rows), 20)
        self.assertEqual({(r["borough"], r["group"]) for r in self.rows},
                         {(b, g) for b in BOROUGHS for g in GROUPS})
        self.assertTrue(all(set(r) == {"borough", "group", "requests"}
                            and type(r["requests"]) is int and r["requests"] >= 550
                            for r in self.rows))

    def test_no_record_level_fields_or_live_data(self):
        self.assertNotRegex(self.html.lower(),
                            r'"(?:unique_key|incident_address|latitude|longitude|descriptor|closed_date|status)"\s*:')
        self.assertNotIn("fetch(", self.html)
        self.assertNotIn("XMLHttpRequest", self.html)
        self.assertIn("NOT A PUBLIC RELEASE", self.html)
        self.assertIn("Research status: HOLD", self.html)

    def test_keyboard_labels_live_region_and_table(self):
        tags = self.parser.tags
        ids = [a["id"] for _, a in tags if "id" in a]
        self.assertEqual(len(ids), len(set(ids)))
        for control in ("borough", "group", "sort", "reset"):
            self.assertIn(control, ids)
            self.assertTrue(any(t == "label" and a.get("for") == control for t, a in tags))
        self.assertTrue(any(t == "p" and a.get("role") == "status"
                            and a.get("aria-live") == "polite" for t, a in tags))
        self.assertEqual(sum(t == "th" and a.get("scope") == "col" for t, a in tags), 3)
        self.assertTrue(any(t == "a" and a.get("href") == "#controls" for t, a in tags))
        self.assertIn("prefers-reduced-motion", self.html)

    def test_local_only_content_policy(self):
        for directive in ("connect-src 'none'", "default-src 'none'", "form-action 'none'"):
            self.assertIn(directive, self.html)
        self.assertNotRegex(self.html, r'<(?:iframe|img|form)\b')

if __name__ == "__main__":
    unittest.main()
