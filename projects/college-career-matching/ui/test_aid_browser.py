"""Synthetic aid-category browser regression; no real institutional records."""
import unittest
from playwright.async_api import async_playwright
from test_browser import local_server

class AidBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_aid_categories_and_unknown(self):
        server = local_server()
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    await page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
                    assert await page.locator(".result").count() == 4
                    await page.locator("#aid-type").select_option("merit")
                    assert await page.locator(".result").count() == 2
                    assert "individual eligibility unverified" in await page.locator("#results").inner_text()
                    await page.locator("#aid-type").select_option("need-based")
                    assert await page.locator(".result").count() == 4
                    await page.evaluate("""() => {
                        DATA = [DATA[0], {...DATA[0], name:"Unknown aid", aid:null},
                                {...DATA[0], name:"No documented aid", aid:[]}];
                        render();
                    }""")
                    assert await page.locator(".result").count() == 1, "Unknown and empty aid must fail strict category filter"
                    await page.locator("#aid-type").select_option("any")
                    assert await page.locator(".result").count() == 3, "No aid requirement preserves unknown records"
                    assert not errors, errors
                finally:
                    await browser.close()
        finally:
            server.shutdown()
            server.server_close()
