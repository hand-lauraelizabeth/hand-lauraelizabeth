"""Enforce Sprint 1 asset and visible-page budgets against the real data."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "college-search-sprint1.html"
DATA = ROOT / "data/sprint1/college-search-national.v1.json"
DATA_GZIP = ROOT / "data/sprint1/college-search-national.v1.json.gz"
URL = "http://127.0.0.1:8765/college-search-sprint1.html"
PAGE_SIZE = 24


def test_sizes():
    html = HTML.read_bytes()
    dataset = DATA.read_bytes()
    compressed = DATA_GZIP.read_bytes()
    assert len(compressed) < 500 * 1024, "Dataset >500 KiB compressed"
    assert gzip.decompress(compressed) == dataset, "Gzip payload mismatch"
    assert len(gzip.compress(html, compresslevel=9)) < 75 * 1024, "UI >75 KiB compressed"
    payload = json.loads(dataset)
    assert len(payload["institutions"]) == 6243
    assert html.count(b'data-src="./data/sprint1/college-search-national.v1.json"') == 1
    assert b"<details id=\"cs-about-data\"" in html
    print("PERFORMANCE ASSETS PASS", json.dumps({
        "institutions": 6243, "dataset_gzip_bytes": len(compressed),
        "ui_gzip_bytes": len(gzip.compress(html, compresslevel=9)),
        "max_dataset_bytes": 500 * 1024, "max_ui_bytes": 75 * 1024,
        "data_sources": 1
    }, sort_keys=True))


def test_visible_cards():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        requests = []
        errors = []
        page.on("request", lambda request: requests.append(request.url)
                if request.url.endswith("college-search-national.v1.json") else None)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(URL, wait_until="domcontentloaded")
        page.locator("#cs-results-section").wait_for(state="visible", timeout=30000)
        assert page.locator(".cs-card").count() == PAGE_SIZE
        assert "6,243 schools found" in page.locator("#cs-result-count").inner_text()
        assert len(requests) == 1, f"Expected one dataset request, got {len(requests)}"
        page.locator("#cs-name").fill("University")
        assert page.locator(".cs-card").count() == PAGE_SIZE, "Filtering renders hidden/unneeded cards"
        page.locator("#cs-sort").select_option("name-desc")
        assert page.locator(".cs-card").count() == PAGE_SIZE, "Sorting renders hidden/unneeded cards"
        page.locator("#cs-state").select_option("NY")
        assert page.locator(".cs-card").count() <= PAGE_SIZE, "State filtering renders excess cards"
        page.locator("#cs-clear").click()
        assert page.locator(".cs-card").count() == PAGE_SIZE, "Clear must restore 24 cards, not all data"
        page.locator("#cs-show-more").click()
        assert page.locator(".cs-card").count() == 2 * PAGE_SIZE, "Show more must add one batch"
        assert len(requests) == 1, "Filters must not refetch the national dataset"
        assert not errors, errors
        print("PERFORMANCE DOM PASS", json.dumps({
            "initial_cards": PAGE_SIZE, "cards_after_show_more": 2 * PAGE_SIZE,
            "total_institutions": 6243, "data_requests": len(requests),
            "page_errors": len(errors)
        }, sort_keys=True))
        browser.close()


if __name__ == "__main__":
    test_sizes()
    test_visible_cards()
