"""S2-02 UI wiring smoke: all three controls really filter the verified v2 records.
This is browser integration verification; exhaustive combination unit tests are S2-04.
"""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data/sprint2/college-search-national.v2.json").read_text())
RECORDS = list(DATA["institutions"].values())
URL = "http://127.0.0.1:8766/college-search-sprint2.html"


def expected_count(field, value):
    if field == "control":
        return sum(row["control"] == value for row in RECORDS)
    if field == "locale":
        return sum(row["locale"] == value for row in RECORDS)
    if field == "size":
        def match(size):
            if size is None:
                return False
            if value == "under-5000":
                return size < 5000
            if value == "5000-14999":
                return 5000 <= size < 15000
            return size >= 15000
        return sum(match(row["undergraduate_size"]) for row in RECORDS)
    raise ValueError(field)


def actual_count(page):
    text = page.locator("#cs-result-count").inner_text()
    match = re.search(r"^([\d,]+) schools? found", text)
    assert match, text
    return int(match.group(1).replace(",", ""))


def main():
    assert len(RECORDS) == 6243
    combinations = {
        "control": ("public", "private_nonprofit", "private_for_profit"),
        "locale": ("city", "suburb", "town", "rural"),
        "size": ("under-5000", "5000-14999", "15000-plus"),
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for width in (390, 1440):
            page = browser.new_page(viewport={"width":width, "height":844})
            errors = []
            responses = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("response", lambda r: responses.append(r.status)
                    if "college-search-national.v2.json" in r.url else None)
            page.goto(URL, wait_until="domcontentloaded", timeout=20000)
            page.locator("#cs-results-section").wait_for(state="visible", timeout=30000)
            assert actual_count(page) == 6243
            assert page.locator(".cs-card").count() == 24
            assert page.locator("#cs-state option").count() == 60
            assert responses == [200], responses
            for field, values in combinations.items():
                control = page.locator("#cs-" + field)
                assert control.is_enabled(), field
                option_counts = []
                for option in values:
                    control.select_option(option)
                    observed = actual_count(page)
                    expected = expected_count(field, option)
                    assert observed == expected, (width, field, option, observed, expected)
                    assert 0 < observed < 6243, (field, option, observed)
                    assert page.locator(".cs-card").count() == min(24, observed)
                    option_counts.append(observed)
                    page.locator("#cs-clear").click()
                    assert control.input_value() == "", (field, option)
                    assert actual_count(page) == 6243
                assert len(set(option_counts)) > 1, (field, option_counts)

            page.locator("#cs-control").select_option("public")
            page.locator("#cs-locale").select_option("city")
            page.locator("#cs-size").select_option("under-5000")
            expected = sum(r["control"] == "public" and r["locale"] == "city"
                           and r["undergraduate_size"] is not None and
                           r["undergraduate_size"] < 5000 for r in RECORDS)
            assert actual_count(page) == expected, (width, actual_count(page), expected)
            assert 0 < expected < 6243
            page.locator("#cs-name").fill("University")
            page.locator("#cs-state").select_option("NY")
            assert actual_count(page) <= expected
            page.locator("#cs-clear").click()
            assert actual_count(page) == 6243
            for field in ("name", "state", "sort", "control", "locale", "size"):
                value = page.locator("#cs-" + field).input_value()
                assert value == ("name-asc" if field == "sort" else ""), (field, value)
            assert page.locator("#cs-show-more").is_visible()
            page.locator("#cs-show-more").click()
            assert page.locator(".cs-card").count() == 48
            assert not errors, errors
            assert len(responses) == 1, responses
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
            print("SPRINT2_CONTROL_UI_PASS",json.dumps({
                "width":width,"school_count":6243,"three_new_controls":True,
                "nondefault_options_tested":sum(map(len,combinations.values())),
                "combined_count":expected,"data_requests":len(responses),
                "page_errors":len(errors),"cards_after_show_more":48
            },sort_keys=True))
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
