"""Browser smoke tests for the standalone matcher.

Run with: python -m pip install playwright
          python -m playwright install chromium
          python projects/college-career-matching/ui/test_browser.py

Uses only local files and an intercepted dataset URL; no live institutional data.
"""
import asyncio
import json
import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def local_server():
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server



async def main():
    server = local_server()
    try:
      url = f"http://127.0.0.1:{server.server_port}/index.html"
      async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.route("**/public-data.json", lambda route: route.fulfill(status=404, body=""))
        await page.goto(url)
        await page.locator(".result").first.wait_for()
        assert await page.locator(".result").count() == 4, "Expected four synthetic examples"
        assert "synthetic" in (await page.locator("#data-mode").inner_text()).lower()

        await page.locator("#cost").fill("0")
        assert await page.locator(".result").count() == 0, "Zero-cost constraint should filter nonzero records"
        await page.locator("#cost").fill("25000")
        await page.locator("#housing").select_option("required")
        assert await page.locator(".result").count() == 2, "Housing constraint must exclude commuter records"
        await page.locator("#housing").select_option("any")

        await page.set_viewport_size({"width": 375, "height": 812})
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Mobile horizontal overflow"

        # A file named public-data.json must never load without a separate publication gate.
        public_requests = []
        page.on("request", lambda request: public_requests.append(request.url)
                if request.url.endswith("/public-data.json") else None)
        await page.reload()
        await page.locator(".result").first.wait_for()
        assert await page.locator(".result").count() == 4
        assert not public_requests, "Unapproved institutional JSON must not be requested"
        assert "synthetic" in (await page.locator("#data-mode").inner_text()).lower()

        # Inject synthetic adversarial values in memory to test HTML escaping and unknown evidence.
        record = {
            "name": "<img src=x onerror=alert(1)>",
            "setting": None, "housing": None, "access": None,
            "cost": {"0_30k": 0, "30_48k": None, "48_75k": 5000,
                     "75_110k": 9000, "110k_plus": 12000},
            "careers": {"data": None, "education": 0, "health": 2, "business": 3},
            "aid": ["<svg onload=alert(1)>"], "note": "<script>alert(1)</script>",
        }
        await page.evaluate("(record) => { DATA = [record]; render(); }", record)
        assert await page.locator(".result").count() == 1
        assert await page.locator(".result img, .result svg, .result script").count() == 0
        assert "accessibility information unavailable" in await page.locator(".result").inner_text()
        assert "career alignment information unavailable" in await page.locator(".result").inner_text()
        assert "range reflects missing evidence" in await page.locator(".result .score").inner_text()
        await page.locator("#cost").fill("0")
        assert await page.locator(".result").count() == 1, "Zero cost must remain eligible"
        await page.locator("#cost").fill("25000")
        await page.locator("#income").select_option("30_48k")
        assert await page.locator(".result").count() == 0, "Unknown net price fails a cost ceiling"
        await page.locator("#cost").fill("")
        assert await page.locator(".result").count() == 1, "Unknown price visible without ceiling"
        assert "net price unavailable" in await page.locator(".result").inner_text()
        await page.locator("#housing").select_option("required")
        assert "housing availability unverified" in await page.locator(".result").inner_text()
        await page.reload()
        assert await page.locator(".result").count() == 4
        assert not public_requests, "Page reload must never fetch unapproved data"
        assert not errors, f"Browser errors: {errors}"
        await browser.close()
        print("PASS: synthetic filters, mobile overflow, institutional-data load disabled, missing evidence, HTML escaping, zero-cost eligibility")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    asyncio.run(main())
