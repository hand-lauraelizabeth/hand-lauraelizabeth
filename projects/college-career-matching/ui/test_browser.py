"""Browser smoke tests for the standalone matcher.

Run with: python -m pip install playwright
          python -m playwright install chromium
          python projects/college-career-matching/ui/test_browser.py

Uses only local files and an intercepted dataset URL; no live institutional data.
"""
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent
URL = (ROOT / "index.html").as_uri()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.route("**/public-data.json", lambda route: route.fulfill(status=404, body=""))
        await page.goto(URL)
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

        record = {
            "name": "<img src=x onerror=alert(1)>",
            "setting": "Urban", "housing": True, "access": None,
            "cost": {"low": 0, "mid": None, "high": 12000},
            "careers": {"data": None, "education": 0, "health": 2, "business": 3},
            "aid": ["<svg onload=alert(1)>"], "note": "<script>alert(1)</script>",
            "source": "Source <test>", "reference_year": 2025
        }
        await page.unroute("**/public-data.json")
        await page.route("**/public-data.json", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"schema_version": 1, "records": [record]})))
        await page.reload()
        await page.locator(".result").first.wait_for()
        assert "source-attributed" in await page.locator("#data-mode").inner_text()
        assert await page.locator(".result img, .result svg, .result script").count() == 0, "Unescaped HTML inserted"
        assert "accessibility information unavailable" in await page.locator(".result").inner_text()
        assert "career alignment information unavailable" in await page.locator(".result").inner_text()
        await page.locator("#cost").fill("0")
        assert await page.locator(".result").count() == 1, "A zero-cost public record should remain eligible"
        await page.locator("#cost").fill("25000")
        await page.unroute("**/public-data.json")
        invalid = dict(record)
        invalid["cost"] = {"low": 0, "high": 12000}
        await page.route("**/public-data.json", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"schema_version": 1, "records": [invalid]})))
        await page.reload()
        await page.locator(".result").first.wait_for()
        assert "synthetic" in (await page.locator("#data-mode").inner_text()).lower(), "Incomplete record must not replace synthetic mode"
        assert await page.locator(".result").count() == 4
        assert not errors, f"Browser errors: {errors}"
        await browser.close()
        print("PASS: synthetic filters, mobile overflow, public-data loader, missing evidence, HTML escaping, zero-cost eligibility, incomplete-data fallback")


if __name__ == "__main__":
    asyncio.run(main())
