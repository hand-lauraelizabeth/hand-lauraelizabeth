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

    def test_runtime_allowlist_rejects_balanced_tampering_and_bad_schema(self):
        """Execute the committed browser validator independently in Node."""
        import copy
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("Node unavailable; local Chromium regression is recorded separately")
        start = self.html.index("const EXPECTED_COUNTS=")
        end = self.html.index("function initialize(){", start)
        validator = self.html[start:end]
        base = copy.deepcopy(self.rows)
        cases = [base]
        changed = copy.deepcopy(base)
        changed[0]["requests"] += 1
        cases.append(changed)
        balanced = copy.deepcopy(base)
        balanced[0]["requests"] += 1
        balanced[1]["requests"] -= 1
        cases.append(balanced)
        missing = copy.deepcopy(base)
        missing.pop()
        cases.append(missing)
        duplicate = copy.deepcopy(base)
        duplicate[1] = copy.deepcopy(duplicate[0])
        cases.append(duplicate)
        extra = copy.deepcopy(base)
        extra[0]["unique_key"] = "synthetic"
        cases.append(extra)
        floating = copy.deepcopy(base)
        floating[0]["requests"] = 810.5
        cases.append(floating)
        unknown = copy.deepcopy(base)
        unknown[0]["borough"] = "Unspecified"
        cases.append(unknown)
        reordered = list(reversed(copy.deepcopy(base)))
        cases.append(reordered)
        script = validator + "\\nconst cases=JSON.parse(process.argv[1]);process.stdout.write(JSON.stringify(cases.map(validateFixture)));"
        run = subprocess.run([node, "-e", script, json.dumps(cases)],
                             capture_output=True, text=True, timeout=15, check=True)
        self.assertEqual(json.loads(run.stdout),
                         [True, False, False, False, False, False, False, False, True])

    def test_invalid_fixture_is_accessibly_fail_closed(self):
        self.assertIn("function initialize(){", self.html)
        self.assertIn("if(!validateFixture(candidate))", self.html)
        self.assertIn("results.replaceChildren();", self.html)
        self.assertIn("summary.setAttribute('role','alert')", self.html)
        self.assertIn("summary.setAttribute('aria-live','assertive')", self.html)
        self.assertIn("control.disabled=true", self.html)
        self.assertIn("No counts are shown.", self.html)
        self.assertIn("initialize();", self.html)

if __name__ == "__main__":
    unittest.main()
