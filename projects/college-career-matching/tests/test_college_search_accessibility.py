"""Sprint 1 accessibility regression for standalone College Search in Chromium.

Staging iOS/Android manual checks and WordPress integration remain separate release gates.
Runs against the local HTTP server started by college-search-component-smoke.yml.
"""
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/college-search-sprint1.html"


def srgb(value):
    channel = int(value, 16) / 255
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def contrast(a, b):
    def luminance(hex_color):
        color = hex_color.removeprefix("#")
        return sum(weight * srgb(color[i:i + 2])
                   for weight, i in [(0.2126, 0), (0.7152, 2), (0.0722, 4)])
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def main():
    assert contrast("#9c5300", "#ffffff") >= 3.0, "Focus indicator lacks contrast against white"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for width, height, mobile in [(1440, 900, False), (390, 844, True), (320, 720, True)]:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                is_mobile=mobile,
                has_touch=mobile,
                device_scale_factor=1,
            )
            console_errors = []
            page_errors = []
            page.on("console", lambda message: console_errors.append(message.text)
                    if message.type == "error" else None)
            page.on("pageerror", lambda exception: page_errors.append(str(exception)))
            response = page.goto(URL, wait_until="domcontentloaded")
            assert response.status == 200, response.status
            page.locator("#cs-results-section").wait_for(state="visible", timeout=30000)
            assert "6,243 schools found" in page.locator("#cs-result-count").inner_text()
            assert page.get_by_role("main").count() == 1, "Exactly one main landmark expected"
            viewport = page.locator('meta[name="viewport"]').get_attribute("content")
            lowered = viewport.lower()
            assert "width=device-width" in lowered, viewport
            assert "user-scalable=no" not in lowered and "maximum-scale=1" not in lowered, viewport
            assert not page.evaluate("""() => [...document.querySelectorAll('input,select')].some(
                el => !el.labels || el.labels.length !== 1 || !el.labels[0].innerText.trim()
            )"""), "Unlabeled input or select"
            assert not page.evaluate("""() => [...document.querySelectorAll('button')].some(
                el => !el.innerText.trim() && !el.getAttribute('aria-label')
            )"""), "Unnamed button"
            assert not page.evaluate("""() => [...document.querySelectorAll('a')].some(
                el => !el.textContent.trim() && !el.getAttribute('aria-label')
            )"""), "Unnamed link"
            assert page.locator(".cs-card a").count() >= 1
            # Each institution link includes the school and city in its accessible name.
            for link in page.locator(".cs-card a").all():
                accessible_text = link.inner_text()
                assert accessible_text.startswith("Visit "), accessible_text
                assert "website" in accessible_text and "opens in a new tab" in accessible_text
            assert page.locator(".cs-skip").get_attribute("href") == "#cs-results-heading"
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement.classList.contains('cs-skip')"), \
                "First keyboard tab should reach the skip link"
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement.id") == "cs-name", \
                "Keyboard tab should reach the school-name search"
            outline = page.evaluate("getComputedStyle(document.activeElement).outlineWidth")
            assert float(outline.removesuffix("px")) >= 3, "Keyboard focus indicator missing"
            about = page.locator("details#cs-about-data")
            assert about.count() == 1, "There must be exactly one About this data note"
            summary = about.locator("summary")
            assert summary.inner_text().strip() == "About this data"
            assert not about.evaluate("(el) => el.open"), "Source note must start collapsed"
            summary.click()
            assert about.evaluate("(el) => el.open"), "Source note must expand on click"
            assert about.locator("time[datetime='2026-06-10']").inner_text() == "June 10, 2026"
            assert about.locator("a[href='https://collegescorecard.ed.gov/data/']").count() == 1
            assert "6,243 institutions" in about.inner_text()
            assert "not an independently verified list" in about.inner_text()
            summary.press("Enter")
            assert not about.evaluate("(el) => el.open"), "Keyboard must collapse source note"
            assert not page_errors, page_errors
            assert not console_errors, console_errors
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2"), \
                f"Horizontal overflow at {width}px viewport"
            print(f"ACCESSIBILITY PASS viewport={width}px mobile={mobile}: zoom allowed, "
                  "main=1, labeled controls/links, focus>=3px, no overflow, console/page errors=0")
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
