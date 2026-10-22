"""Chromium layout smoke test for the public-records form.

Run: python -m pip install playwright && python -m playwright install chromium
     python free-tools/public-records/browser-reflow-review.test.py

This exercises rendered CSS and keyboard focus in an isolated document.
It does not establish HTTP-served CSP, native browser zoom, or screen-reader support.
"""
from pathlib import Path
import re
import unittest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent

class ReflowReview(unittest.TestCase):
    def test_layout_labels_and_keyboard_at_narrow_widths(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        css = (ROOT / 'styles.css').read_text(encoding='utf-8')
        # This test only assesses CSS layout. A separate HTTP test must assess CSP.
        html = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', '', html)
        html = html.replace('<link rel="stylesheet" href="styles.css">', '<style>' + css + '</style>')
        html = html.replace('<script type="module" src="app.mjs"></script>', '')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for width in (320, 375, 1280):
                    with self.subTest(width=width):
                        page = browser.new_page(viewport={'width': width, 'height': 900})
                        try:
                            page.set_content(html)
                            metrics = page.evaluate("""() => ({
                              viewport: innerWidth,
                              scroll: document.documentElement.scrollWidth,
                              mainCount: document.querySelectorAll('main').length,
                              statusRole: document.getElementById('status')?.getAttribute('role'),
                              missingLabels: [...document.querySelectorAll('input,select,textarea')]
                                .filter(el => !el.labels?.length).length
                            })""")
                            self.assertLessEqual(metrics['scroll'], metrics['viewport'])
                            self.assertEqual(metrics['mainCount'], 1)
                            self.assertEqual(metrics['statusRole'], 'status')
                            self.assertEqual(metrics['missingLabels'], 0)
                            page.keyboard.press('Tab')
                            self.assertEqual(page.evaluate('document.activeElement.tagName'), 'A')
                        finally:
                            page.close()
            finally:
                browser.close()

if __name__ == '__main__':
    unittest.main()
