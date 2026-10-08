"""Standalone synthetic matcher browser smoke and regression checks."""
import asyncio
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
            errors, public_requests = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: public_requests.append(request.url)
                    if request.url.endswith("/public-data.json") else None)
            await page.route("**/public-data.json",
                             lambda route: route.fulfill(status=404, body=""))
            await page.goto(url)
            await page.locator(".result").first.wait_for()
            assert await page.locator(".result").count() == 4
            assert "synthetic" in (await page.locator("#data-mode").inner_text()).lower()
            await page.locator("#cost").fill("0")
            assert await page.locator(".result").count() == 0
            await page.locator("#cost").fill("25000")
            await page.locator("#housing").select_option("required")
            assert await page.locator(".result").count() == 2
            await page.locator("#housing").select_option("any")
            await page.set_viewport_size({"width": 375, "height": 812})
            assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            await page.reload()
            assert await page.locator(".result").count() == 4
            assert not public_requests, "Unapproved data must not be requested"

            # All injected values below are synthetic; markup must be escaped.
            record = {
                "name": "<em>Example</em>", "setting": None, "housing": None,
                "access": None,
                "cost": {"0_30k": 0, "30_48k": None, "48_75k": 5000,
                         "75_110k": 9000, "110k_plus": 12000},
                "careers": {"data": None, "education": 0, "health": 2, "business": 3},
                "aid": ["<mark>Example</mark>"], "note": "<small>Example</small>",
            }
            await page.evaluate("(record) => { DATA = [record]; render(); }", record)
            assert await page.locator(".result").count() == 1
            assert await page.locator(".result em, .result mark, .result small").count() == 0
            assert "<em>Example</em>" in await page.locator(".result").inner_text()
            assert await page.locator("#access-feature").count() == 1
            assert "career alignment information unavailable" in await page.locator(".result").inner_text()
            assert "range reflects missing evidence" in await page.locator(".result .score").inner_text()
            await page.locator("#cost").fill("0")
            assert await page.locator(".result").count() == 1, "Zero net price remains eligible"
            await page.locator("#cost").fill("25000")
            await page.locator("#income").select_option("30_48k")
            assert await page.locator(".result").count() == 0, "Unknown price fails cost ceiling"
            await page.locator("#cost").fill("")
            assert await page.locator(".result").count() == 1, "Unknown price allowed without ceiling"
            assert "net price unavailable" in await page.locator(".result").inner_text()

            await page.locator("#housing").select_option("required")
            assert await page.locator(".result").count() == 0, "Unknown housing excluded"
            await page.evaluate("() => { DATA[0].housing = false; render(); }")
            assert await page.locator(".result").count() == 0, "Documented no excluded"
            await page.evaluate("() => { DATA[0].housing = true; render(); }")
            assert await page.locator(".result").count() == 1, "Positive housing included"
            await page.evaluate("() => { DATA[0].housing = null; render(); }")
            await page.locator("#housing").select_option("any")
            assert await page.locator(".result").count() == 1, "Unknown visible without strict constraint"
            assert "Housing unverified" in await page.locator(".result").inner_text()
            await page.reload()
            assert await page.locator(".result").count() == 4
            assert not public_requests
            assert not errors, f"Browser errors: {errors}"
            await browser.close()
            print("PASS: synthetic data, responsive layout, escaping, missing evidence, cost and strict housing")
    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    asyncio.run(main())
