"""Browser regression for the NYC 311 borough explorer.

Run: python tests/test_borough_explorer_browser.py
Requires playwright (Python) and Chromium. This test does not access the network.
"""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[1] / "preview" / "borough-explorer.html"
assert HTML.is_file(), HTML

with sync_playwright() as p:
    binary = os.getenv("CHROMIUM_BIN") or shutil.which("chromium") or shutil.which("chromium-browser")
    browser = p.chromium.launch(executable_path=binary, headless=True, args=["--no-sandbox"])
    checks = 0
    for width, height in [(1440, 900), (390, 844), (320, 700)]:
        page = browser.new_page(viewport={"width": width, "height": height}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content(HTML.read_text(encoding="utf-8"), wait_until="load")
        assert page.locator("main").count() == 1
        assert page.locator("h1").count() == 1
        assert page.locator("label[for=area]").count() == 1
        assert page.locator("#bars [role=listitem]").count() == 6
        assert page.locator("#rows tr").count() == 6
        assert "323,627" in page.locator("#summary").inner_text()
        checks += 6

        page.locator("#area").select_option("Queens")
        assert page.locator("#bars [role=listitem]").count() == 1
        assert page.locator("#rows tr").count() == 1
        assert "80,443" in page.locator("#summary").inner_text()
        checks += 3
        with page.expect_download() as d:
            page.locator("#csv").click()
        download = d.value
        csv = Path(download.path()).read_text(encoding="utf-8-sig")
        assert download.suggested_filename.endswith(".csv")
        assert "Queens" in csv and "80443" in csv
        assert "Brooklyn" not in csv
        checks += 3

        page.locator("#reset").click()
        assert page.locator("#bars [role=listitem]").count() == 6
        assert page.locator("#area").input_value() == "all"
        assert page.locator("#sort").input_value() == "desc"
        checks += 3

        page.locator("#sort").select_option("alpha")
        assert "Bronx" in page.locator("#bars [role=listitem]").first.inner_text()
        page.locator("#first").select_option("Queens")
        page.locator("#second").select_option("Queens")
        assert "different categories" in page.locator("#difference").inner_text()
        page.locator("#second").select_option("Brooklyn")
        assert "25,261 fewer" in page.locator("#difference").inner_text()
        checks += 4

        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"overflow at {width}px"
        assert not errors, errors
        checks += 2
        page.close()
    browser.close()
print(f"PASS: {checks} assertions across three desktop/mobile viewports")
