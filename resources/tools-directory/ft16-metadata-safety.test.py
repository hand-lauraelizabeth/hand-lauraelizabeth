"""Browser-local, synthetic metadata rendering acceptance test. No real user data."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import re

root = Path(__file__).resolve().parent
html = (root / "index.html").read_text()
html = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', "", html)
html = re.sub(r'<link rel="stylesheet"[^>]*>', "", html)
html = re.sub(r'<script type="module"[^>]*></script>', "", html)
payloads = [
    '<img src=x onerror="window.__ft16_executed=1">',
    '<svg onload="window.__ft16_executed=1"></svg>',
    '<script>window.__ft16_executed=1</script>',
]
rows = [dict(id="safe", title="Safe resource", category="Research", status="live",
             description="A benign synthetic entry",
             url="https://www.lauraelizabethhand.com/resources/example/")]
for i, payload in enumerate(payloads):
    rows.append(dict(id=f"fixture-{i}", title=payload, category="Untrusted metadata",
                     status="development", description=f"Description: {payload}"))
js = "const TOOLS=Object.freeze(" + json.dumps(rows) + ");\n"
js += "const STATUS_LABELS=Object.freeze({live:'Live',preview:'Preview',development:'In development'});\n"
js += re.sub(r"^import .*?;\n", "", (root / "directory.mjs").read_text(),
             flags=re.M).replace("export function", "function") + "\n"
js += re.sub(r"^import .*?;\n", "", (root / "app.mjs").read_text(), flags=re.M)
css = "\n".join((root / f).read_text() for f in
                ("styles.css", "layout.css", "controls.css", "focus.css"))
checks = 0
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for width in (320, 375, 1280):
        page = browser.new_page(viewport={"width": width, "height": 800})
        requests, errors = [], []
        page.on("request", lambda r: requests.append(r.url))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content(html)
        page.add_style_tag(content=css)
        page.add_script_tag(content=js)
        def check(condition, label):
            global checks
            assert condition, f"{width}px: {label}"
            checks += 1
        check(page.locator(".ft15-card").count() == 4, "four entries")
        check(page.locator(".ft15-link").count() == 1, "one live link")
        check(page.locator(".ft15-unavailable").count() == 3, "three unavailable")
        check(page.locator('script:not([type="module"])').count() == 1, "only test script")
        check(page.locator(".ft15-card img, .ft15-card svg, .ft15-card script").count() == 0, "no parsed markup")
        check(page.evaluate("window.__ft16_executed===undefined"), "no script execution")
        check(not requests, "no network requests")
        check(not errors, "no JavaScript errors")
        for payload in payloads:
            check(page.locator(".ft15-card h3").filter(has_text=payload).count() == 1, "literal title")
            check(page.locator(".ft15-card p").filter(has_text=payload).count() == 1, "literal description")
        page.locator("#tool-query").fill("fixture")
        check(page.locator(".ft15-card").count() == 0, "IDs not search text")
        page.locator("#tool-query").fill("<script>")
        check(page.locator(".ft15-card").count() == 1, "literal text search")
        page.locator("#tool-clear").click()
        check(page.locator(".ft15-card").count() == 4, "reset")
        check(page.evaluate("document.documentElement.scrollWidth<=innerWidth"), "reflow")
        page.close()
    browser.close()
print(f"FT-16 metadata safety acceptance: {checks} Chromium assertions PASS")
