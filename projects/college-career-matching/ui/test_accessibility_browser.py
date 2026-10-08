"""Browser checks for synthetic accessibility evidence controls."""
import asyncio
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
            assert not errors, errors
            await browser.close()
            print("PASS: feature-specific synthetic accessibility browser controls")
    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    asyncio.run(main())
