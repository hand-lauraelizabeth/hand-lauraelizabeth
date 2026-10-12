"""S2-06: real-browser accessibility/regression checks for the isolated Sprint 2 build.

Tests locally served, verified 6,243-school v2 data; does not exercise WordPress
theme markup or replace physical-device screen-reader/iOS/Android QA.
"""
import json
import re
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8766/college-search-sprint2.html"
DATA_PATH = "**/data/sprint2/college-search-national.v2.json"
FILTERS = ("name", "state", "sort", "control", "locale", "size")
NAMES = {
    "cs-name": "School name",
    "cs-state": "State or territory",
    "cs-sort": "Sort by",
    "cs-control": "Institution control",
    "cs-locale": "Campus setting",
    "cs-size": "Undergraduate size",
}

def channel(v):
    v = int(v, 16) / 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

def contrast(a, b):
    def lum(color):
        c = color.lstrip("#")
        return sum(w * channel(c[i:i + 2])
                   for w, i in ((0.2126, 0), (0.7152, 2), (0.0722, 4)))
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)

def verify_reflow(page, width, *, zoom=False):
    result = page.evaluate("""() => ({
        scroll: document.documentElement.scrollWidth,
        viewport: document.documentElement.clientWidth,
        extent: innerWidth
    })""")
    assert result["scroll"] <= result["extent"] + 2, (width, zoom, result)

def verify_named_controls(page):
    assert page.get_by_role("main").count() == 1
    assert page.get_by_role("searchbox", name="School name").count() == 1
    for label in ("State or territory", "Sort by", "Institution control",
                  "Campus setting", "Undergraduate size"):
        assert page.get_by_role("combobox", name=label).count() == 1, label
    for label in ("Clear", "Show 24 more"):
        assert page.get_by_role("button", name=label).count() == 1, label
    assert not page.evaluate("""() => [...document.querySelectorAll('input,select')].some(
        el => el.labels.length !== 1 || !el.labels[0].textContent.trim())""")
    assert not page.evaluate("""() => [...document.querySelectorAll('button')].some(
        el => !(el.innerText.trim() || el.getAttribute('aria-label')))""")
    assert not page.evaluate("""() => [...document.querySelectorAll('a')].some(
        el => !(el.textContent.trim() || el.getAttribute('aria-label')))""")
    for key in ("control", "locale", "size"):
        assert page.locator("#cs-" + key).get_attribute("aria-describedby") == "cs-" + key + "-missing"
        assert page.locator("#cs-" + key + "-missing").is_visible()
    assert page.get_by_role("status").count() >= 1
    assert page.locator("#cs-result-count").get_attribute("aria-live") == "polite"
    assert page.locator("#cs-coverage-total").inner_text() == "6,243"
    for link in page.locator(".cs-card a").all():
        label = link.inner_text()
        assert label.startswith("Visit ") and " website" in label, label
        assert "opens in a new tab" in label, label
        assert link.get_attribute("rel") == "noopener noreferrer"

def keyboard_flow(page):
    # Fresh navigation: tab order follows visible DOM order and never strands
    # users in a decorative/inert control.
    for expected in ("", "cs-name", "cs-state", "cs-sort",
                     "cs-control", "cs-locale", "cs-size"):
        page.keyboard.press("Tab")
        if expected == "":
            assert page.evaluate("document.activeElement.classList.contains('cs-skip')")
        else:
            assert page.evaluate("document.activeElement.id") == expected, expected
        style = page.evaluate("""() => {
            const s = getComputedStyle(document.activeElement);
            return {w:parseFloat(s.outlineWidth),style:s.outlineStyle,color:s.outlineColor}
        }""")
        assert style["w"] >= 3 and style["style"] != "none", (expected, style)

    # Native select responds to keyboard; results and Clear change immediately.
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Tab")
    assert page.locator("#cs-size").input_value() == "under-5000"
    assert page.locator("#cs-active-list li").all_inner_texts() == [
        "Undergraduate size: Under 5,000"
    ]
    assert page.locator("#cs-clear").is_enabled()
    page.locator("#cs-clear").focus()
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.id") == "cs-name"
    assert all(page.locator("#cs-" + key).input_value() ==
               ("name-asc" if key == "sort" else "") for key in FILTERS)
    assert page.locator("#cs-active-none").is_visible()

    # A search with no matches has an announced count and visible guidance.
    page.keyboard.type("QZX_NONEXISTENT_COLLEGE_ACCESSIBILITY_934")
    assert page.locator("#cs-result-count").inner_text() == "0 schools found"
    assert page.locator("#cs-empty").is_visible()
    assert "No schools match" in page.locator("#cs-empty").inner_text()
    assert page.locator("#cs-show-more").is_hidden()
    assert page.locator("#cs-active-list").is_visible()
    assert page.locator("#cs-results-list li").count() == 0
    page.locator("#cs-clear").focus()
    page.keyboard.press("Space")
    assert page.locator("#cs-empty").is_hidden()
    assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools found")
    assert page.evaluate("document.activeElement.id") == "cs-name"

    about = page.locator("details#cs-about-data")
    assert about.count() == 1 and not about.evaluate("(el) => el.open")
    summary = about.locator("summary")
    assert summary.inner_text().strip() == "About this data"
    summary.focus()
    page.keyboard.press("Enter")
    assert about.evaluate("(el) => el.open")
    assert about.locator("time[datetime='2026-06-10']").count() == 1
    assert about.locator("a[href='https://collegescorecard.ed.gov/data/']").count() == 1
    page.keyboard.press("Enter")
    assert not about.evaluate("(el) => el.open")

def retry_flow(page):
    # Synthesize a successfully transported but invalid response to test
    # fail-closed handling without treating an expected network abort's Chrome
    # "Failed to load resource" diagnostic as an app console error.
    page.route(DATA_PATH, lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=json.dumps({"source":"invalid", "institutions":{}})))
    page.reload(wait_until="domcontentloaded")
    page.locator("#cs-error").wait_for(state="visible", timeout=30000)
    assert page.get_by_role("alert").count() == 1
    assert "Unable to load and verify" in page.get_by_role("alert").inner_text()
    assert page.locator("#cs-results-section").is_hidden()
    assert page.locator("#cs-data-completeness").is_hidden()
    assert page.locator(".cs-card").count() == 0
    for key in FILTERS:
        assert page.locator("#cs-" + key).is_disabled(), key
    retry = page.get_by_role("button", name="Retry loading")
    assert retry.is_visible() and retry.is_enabled()
    page.unroute(DATA_PATH)
    retry.focus()
    page.keyboard.press("Enter")
    page.locator("#cs-results-section").wait_for(state="visible", timeout=30000)
    assert page.locator("#cs-error").is_hidden()
    assert page.locator("#cs-data-completeness").is_visible()
    assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools found")
    assert page.locator(".cs-card").count() == 24
    assert page.locator("#cs-name").is_enabled()

def main():
    assert contrast("#9c5300", "#ffffff") >= 3.0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for width, height, mobile in ((1440, 900, False), (390, 844, True), (320, 720, True)):
            page = browser.new_page(
                viewport={"width":width,"height":height},
                is_mobile=mobile,has_touch=mobile,device_scale_factor=1)
            console_errors, page_errors = [], []
            page.on("console", lambda message: console_errors.append(message.text)
                    if message.type == "error" else None)
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            response = page.goto(URL, wait_until="domcontentloaded")
            assert response.status == 200
            page.locator("#cs-results-section").wait_for(state="visible", timeout=30000)
            assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools found")
            viewport = page.locator('meta[name="viewport"]').get_attribute("content").lower()
            assert "width=device-width" in viewport
            assert not re.search(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1(?:\D|$)",viewport)
            verify_reflow(page,width)
            verify_named_controls(page)
            keyboard_flow(page)
            retry_flow(page)
            # Emulate 200% page zoom and check that no content is clipped
            # horizontally; 320px viewport also covers narrow reflow.
            page.evaluate("document.documentElement.style.zoom='2'")
            assert page.evaluate("parseFloat(getComputedStyle(document.documentElement).zoom)") >= 2
            verify_reflow(page,width,zoom=True)
            assert page.locator("#cs-result-count").is_visible()
            assert not page_errors, page_errors
            assert not console_errors, console_errors
            print("SPRINT2_ACCESSIBILITY_PASS",json.dumps({
                "viewport_px":width,"mobile_emulation":mobile,
                "keyboard_labels_focus":True,"zoom_200pct":True,
                "zero_results":True,"error_retry":True,
                "console_errors":len(console_errors),"page_errors":len(page_errors),
            },sort_keys=True))
            page.close()
        browser.close()

if __name__ == "__main__":
    main()
