"""Playwright acceptance tests for strict institutional-policy and applicant inputs.

Synthetic-only: intercepts public-data.json; never loads private institutional data.
"""
import asyncio
import functools
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class MatcherPolicyBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        await self.page.route("**/public-data.json", lambda route: route.fulfill(status=404, body=""))
        await self.page.goto(f"http://127.0.0.1:{self.server.server_port}/index.html")
        await self.page.locator(".result").first.wait_for()

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()
        self.server.shutdown()
        self.server.server_close()

    async def test_policy_gates_scores_sections_and_unknown_size(self):
        page = self.page
        self.assertEqual(await page.locator(".result").count(), 4)
        self.assertIn("synthetic", (await page.locator("#data-mode").inner_text()).lower())
        self.assertEqual(await page.locator(".result .policy-evidence").count(), 4)
        self.assertEqual(await page.locator(".result .policy-evidence a").count(), 0)
        await page.locator("#testingChoice").select_option("test_optional")
        self.assertEqual(await page.locator(".result").count(), 0, "Unverified synthetic policies must not pass optional")
        self.assertIn("independently reviewed", await page.locator("#applicantFeedback").inner_text())
        await page.locator("#testingChoice").select_option("test_blind")
        self.assertEqual(await page.locator(".result").count(), 0, "Unverified synthetic policies must not pass blind")
        await page.locator("#testingChoice").select_option("omit")
        self.assertEqual(await page.locator(".result").count(), 4, "Omitted scores must remain allowed")

        await page.locator("#testingChoice").select_option("sat")
        await page.locator("#satTotal").fill("1200")
        await page.locator("#satReadingWriting").fill("600")
        await page.locator("#satMath").fill("600")
        self.assertEqual(await page.locator(".result").count(), 4)
        await page.locator("#satMath").fill("610")
        self.assertIn("SAT total must equal section sum", await page.locator("#applicantFeedback").inner_text())
        self.assertEqual(await page.locator(".result").count(), 0)
        await page.locator("#satMath").fill("600")
        self.assertEqual(await page.locator(".result").count(), 4)

        await page.locator("#testingChoice").select_option("act")
        await page.locator("#actComposite").fill("25")
        await page.locator("#actEnglish").fill("37")
        self.assertIn("Invalid actEnglish", await page.locator("#applicantFeedback").inner_text())
        self.assertEqual(await page.locator(".result").count(), 0)
        await page.locator("#actEnglish").fill("25")
        self.assertEqual(await page.locator(".result").count(), 4)

        await page.locator("#sizeKind").select_option("undergraduate")
        await page.locator("#sizeMin").fill("1")
        self.assertEqual(await page.locator(".result").count(), 0, "Unknown undergraduate size must fail strict range")
        await page.locator("#sizeKind").select_option("any")
        self.assertEqual(await page.locator(".result").count(), 4)
        self.assertEqual(self.errors, [], f"Browser errors: {self.errors}")


if __name__ == "__main__":
    unittest.main()
