"""Offline browser QA for the pinned NYC 311 September aggregate explorer.

Run: python tests/test_exact_committed_explorer.py
Requires Python Playwright and Chromium; does not access the network.
The Git blob SHA pins the exact previously reviewed HTML, preventing tests
of an unrelated local preview from being mistaken for release evidence.
"""
import csv
import hashlib
import io
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[1] / "preview" / "borough-explorer.html"
raw = HTML.read_bytes()
blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
assert blob == "53fad1023a8e1a50476d95466b3fe5d32e7968b4", (
    "Committed HTML changed: review and update tests before claiming release QA"
)
checks = 0
with sync_playwright() as p:
    binary = os.getenv("CHROMIUM_BIN") or shutil.which("chromium") or shutil.which("chromium-browser")
    browser = p.chromium.launch(executable_path=binary, headless=True, args=["--no-sandbox"])
    for width, height in [(1440, 900), (390, 844), (320, 700)]:
        page = browser.new_page(viewport={"width": width, "height": height}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(raw.decode("utf-8"), wait_until="load")
        assert page.locator("main").count() == 1; checks += 1
        assert page.locator("h1").count() == 1; checks += 1
        assert page.locator("label[for=area]").count() == 1; checks += 1
        assert page.locator("#bars [role=listitem]").count() == 6; checks += 1
        assert page.locator("#rows tr").count() == 6; checks += 1
        assert "323,627" in page.locator("#summary").inner_text(); checks += 1
        assert page.locator("#area option").count() == 7; checks += 1
        assert page.locator("#first option").count() == 6; checks += 1
        assert page.locator("#second option").count() == 6; checks += 1
        page.locator("#area").select_option("Queens")
        assert page.locator("#bars [role=listitem]").count() == 1; checks += 1
        assert page.locator("#rows tr").count() == 1; checks += 1
        assert "80,443" in page.locator("#summary").inner_text(); checks += 1
        with page.expect_download() as download:
            page.locator("#csv").click()
        csv_text = Path(download.value.path()).read_text(encoding="utf-8-sig")
        rows = list(csv.reader(io.StringIO(csv_text)))
        assert len(rows) == 2 and rows[1][:2] == ["Queens", "80443"]; checks += 1
        assert download.value.suggested_filename == "nyc311-2026-09-aggregate-2026-10-16.csv"; checks += 1
        page.locator("#reset").click()
        assert page.locator("#bars [role=listitem]").count() == 6; checks += 1
        assert page.locator("#area").input_value() == "all"; checks += 1
        assert page.locator("#sort").input_value() == "desc"; checks += 1
        page.locator("#sort").select_option("alpha")
        assert "Bronx" in page.locator("#bars [role=listitem]").first.inner_text(); checks += 1
        page.locator("#sort").select_option("asc")
        assert "Unspecified" in page.locator("#bars [role=listitem]").first.inner_text(); checks += 1
        page.locator("#first").select_option("Queens")
        page.locator("#second").select_option("Queens")
        assert "different categories" in page.locator("#difference").inner_text(); checks += 1
        page.locator("#second").select_option("Brooklyn")
        assert "25,261 fewer" in page.locator("#difference").inner_text(); checks += 1
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (
            f"Horizontal overflow at {width}px"
        ); checks += 1
        assert not errors, errors; checks += 1
        assert page.locator('a[href*="data.cityofnewyork.us"]').count() >= 1; checks += 1
        assert "raw-file SHA-256 remain pending" in page.locator("main").inner_text(); checks += 1
        page.close()
    browser.close()
print(f"PASS: {checks} assertions across 3 viewports, exact Git blob verified")
