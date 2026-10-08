"""Browser checks for synthetic accessibility evidence controls."""
import asyncio
import unittest
from playwright.async_api import async_playwright
from test_browser import local_server

async def main():
    server = local_server()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
            assert await page.locator(".result").count() == 4
            await page.locator("#access-feature").select_option("building_access")
            assert await page.locator(".result").count() == 2
            await page.locator("#access-evidence").select_option("include-unknown")
            assert await page.locator(".result").count() == 4
            assert "unknown" in (await page.locator("#results").inner_text()).lower()
            await page.locator("#access-feature").select_option("transit_path_access")
            assert await page.locator(".result").count() == 3
            await page.locator("#access-evidence").select_option("yes")
            assert await page.locator(".result").count() == 1
            assert await page.locator("#filter-summary").get_attribute("aria-live") == "polite"
            assert "1 synthetic matches" in await page.locator("#filter-summary").inner_text()
            # The following records and feature states are synthetic test fixtures only.
            synthetic = {
                "name": "Synthetic evidence boundary case",
                "setting": "Urban", "housing": None,
                "accessibility": {
                    "building_access": "OBSERVED_NO",
                    "transit_path_access": "NOT_PUBLISHED",
                    "academic_accommodations": "NOT_APPLICABLE",
                    "digital_accessibility": "UNKNOWN",
                },
                "cost": {"0_30k": 0, "30_48k": 0, "48_75k": 0,
                         "75_110k": 0, "110k_plus": 0},
                "careers": {"data": 3, "education": 1, "health": 1, "business": 1},
                "aid": [], "note": "Synthetic evidence states."
            }
            await page.evaluate("(record) => { DATA = [record]; render(); }", synthetic)
            await page.locator("#access-evidence").select_option("include-unknown")
            for feature in ("building_access", "transit_path_access", "academic_accommodations"):
                await page.locator("#access-feature").select_option(feature)
                assert await page.locator(".result").count() == 0, (
                    f"{feature}: negative, unpublished and not-applicable must not become unknown"
                )
            await page.locator("#access-feature").select_option("digital_accessibility")
            assert await page.locator(".result").count() == 1, "Unknown is opt-in only"
            await page.locator("#access-evidence").select_option("yes")
            assert await page.locator(".result").count() == 0, "Unknown cannot pass strict yes"
            assert "0 synthetic matches" in await page.locator("#filter-summary").inner_text()
            assert not errors, errors
            await browser.close()
            print("PASS: feature-specific synthetic accessibility browser controls")
    finally:
        server.shutdown()
        server.server_close()

class AccessibilityBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_feature_evidence_states(self):
        await main()

if __name__ == "__main__":
    unittest.main()
