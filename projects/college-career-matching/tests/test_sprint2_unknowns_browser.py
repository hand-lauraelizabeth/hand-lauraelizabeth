"""Sprint 2 S2-03 browser contract: honest unknown counts and exclusion semantics.

Checks the actual component and complete, verified Scorecard v2 national data.
Exhaustive filter boundary unit tests belong to S2-04, not this task.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
rows = list(json.loads((ROOT / "data/sprint2/college-search-national.v2.json").read_text())["institutions"].values())
URL = "http://127.0.0.1:8766/college-search-sprint2.html"
fields = {"control": "control", "locale": "locale", "size": "undergraduate_size"}


def expected():
    return {field: sum(row[source_field] is None for row in rows)
            for field, source_field in fields.items()}


def verify_counts(page, expected_values):
    summary = page.locator("#cs-data-completeness")
    assert summary.is_visible(), "Completeness must appear after validated load"
    assert page.locator("#cs-coverage-total").inner_text() == f"{len(rows):,}"
    assert page.locator("#cs-coverage-title").inner_text().endswith("before filters")
    for field, n in expected_values.items():
        assert page.locator(f"#cs-{field}-unknown").inner_text() == f"{n:,}", (field, n)
        select = page.locator(f"#cs-{field}")
        assert select.get_attribute("aria-describedby") == f"cs-{field}-missing"
        assert page.locator(f"#cs-{field}-missing").is_visible()
    note = page.locator(".cs-coverage-note").inner_text()
    assert "Choosing a value excludes schools with unknown data for that field" in note
    assert "not total enrollment" in note
    assert "never interpreted as rural" in note


def main():
    counts = expected()
    assert len(rows) == 6243
    assert counts == {"control": 0, "locale": 531, "size": 781}, counts
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for width in (390, 1440):
            page = browser.new_page(viewport={"width": width, "height": 844})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(URL, wait_until="domcontentloaded")
            page.locator("#cs-results-section").wait_for(state="visible", timeout=30000)
            verify_counts(page, counts)
            assert "6,243 schools found" in page.locator("#cs-result-count").inner_text()

            # The numbers describe the source universe and do not masquerade
            # as counts within the currently filtered results.
            page.locator("#cs-state").select_option("NY")
            verify_counts(page, counts)
            page.locator("#cs-name").fill("Harvard University")
            assert "0 schools found" in page.locator("#cs-result-count").inner_text()
            verify_counts(page, counts)
            page.locator("#cs-clear").click()

            # No selected size band may include missing size.
            for band in ("under-5000", "5000-14999", "15000-plus"):
                page.locator("#cs-size").select_option(band)
                actual_text = page.locator("#cs-result-count").inner_text()
                values = [r["undergraduate_size"] for r in rows
                          if r["undergraduate_size"] is not None]
                if band == "under-5000":
                    selected = sum(x < 5000 for x in values)
                elif band == "5000-14999":
                    selected = sum(5000 <= x < 15000 for x in values)
                else:
                    selected = sum(x >= 15000 for x in values)
                assert actual_text.startswith(f"{selected:,} school"), (band, actual_text, selected)
                verify_counts(page, counts)
            page.locator("#cs-clear").click()

            # Locale filtering similarly never assigns an unknown campus setting.
            for value in ("city", "suburb", "town", "rural"):
                page.locator("#cs-locale").select_option(value)
                selected = sum(r["locale"] == value for r in rows)
                assert page.locator("#cs-result-count").inner_text().startswith(f"{selected:,} school")
                verify_counts(page, counts)
            page.locator("#cs-clear").click()

            # Failed requests may never leave stale counts visible.
            page.route("**/data/sprint2/college-search-national.v2.json", lambda route: route.abort())
            page.reload(wait_until="domcontentloaded")
            page.locator("#cs-error").wait_for(state="visible", timeout=25000)
            assert page.locator("#cs-data-completeness").is_hidden()
            assert page.locator("#cs-results-section").is_hidden()
            page.unroute("**/data/sprint2/college-search-national.v2.json")
            page.locator("#cs-retry").click()
            page.locator("#cs-results-section").wait_for(state="visible", timeout=30000)
            verify_counts(page, counts)
            assert not errors, errors
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
            print("SPRINT2_UNKNOWNS_BROWSER_PASS", json.dumps({
                "viewport_px": width, "records": len(rows), "unknown": counts,
                "filtered_unknowns_excluded": True,
                "national_denominator_preserved": True,
                "retry_hides_then_restores_summary": True,
                "page_errors": len(errors),
            }, sort_keys=True))
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
