"""Synthetic browser integration checks for Evidence & Timeline local JSON imports.

Requires Python Playwright + Chromium. This runs the committed app module bodies
in a real browser DOM, without HTTP navigation or the production CSP. It is NOT
an HTTP-served, native assistive-technology, or browser-zoom release test.
"""
import json
import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent


def record(source_id, claim):
    return dict(sourceId=source_id, date="2026-10-17", claim=claim,
                status="reported", kind="source", group="")


def fixture(rows):
    return json.dumps({"schema": "evidence-timeline-v1", "records": rows}, ensure_ascii=False).encode()


def run():
    checks = 0

    def check(ok, description):
        nonlocal checks
        assert ok, description
        checks += 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,
                                    executable_path=os.environ.get("CHROMIUM_BIN", "/usr/bin/chromium"),
                                    args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 375, "height": 850}, accept_downloads=True)
        errors, requests, prompts = [], [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: requests.append(r.url))
        html = (ROOT / "index.html").read_text()
        html = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', '', html)
        html = html.replace('<script type="module" src="app.mjs"></script>', '')
        html = html.replace('<link rel="stylesheet" href="styles.css">', '')
        page.set_content(html)
        page.add_style_tag(content=(ROOT / "styles.css").read_text())
        modules = []
        for name in ("exact-core.mjs", "core.mjs", "json-import.mjs", "import-feedback.mjs", "replacement-preview.mjs", "app.mjs"):
            body = (ROOT / name).read_text()
            body = re.sub(r'^import .*?;\s*$', '', body, flags=re.MULTILINE)
            modules.append(re.sub(r'^export ', '', body, flags=re.MULTILINE))
        page.add_script_tag(content="\n".join(modules))
        control = page.locator("#resume-json")
        check(control.get_attribute("aria-describedby") == "resume-json-help", "help text associated")
        page.locator("#sourceId").fill("000123")
        page.locator("#date").fill("2026-10-17")
        page.locator("#claim").fill("Original synthetic")
        page.get_by_role("button", name="Add record").click()
        check(page.locator("#count").inner_text().startswith("1 record"), "manual entry")
        rows = [record("000123", "Changed synthetic"), record("café", "Composed"), record("cafe\u0301", "Decomposed")]

        def cancel(dialog):
            prompts.append(dialog.message)
            dialog.dismiss()

        page.once("dialog", cancel)
        control.set_input_files({"name": "synthetic.json", "mimeType": "application/json", "buffer": fixture(rows)})
        page.locator("#resume-json-status").get_by_text("Import cancelled", exact=False).wait_for()
        check(page.locator("#count").inner_text().startswith("1 record"), "cancel preserves records")
        check("1 changed" in prompts[0] and "2 new" in prompts[0], "accurate preview")
        check(all(s not in prompts[0] for s in ("000123", "café", "synthetic")), "preview contains counts only")
        check(control.input_value() == "", "cancel clears input")

        page.once("dialog", lambda d: d.accept())
        control.set_input_files({"name": "synthetic.json", "mimeType": "application/json", "buffer": fixture(rows)})
        page.locator("#resume-json-status").get_by_text("3 records imported", exact=False).wait_for()
        check(page.locator("#count").inner_text().startswith("3 records"), "replacement applied")
        with page.expect_download() as event:
            page.locator("#json").click()
        exported = json.loads(Path(event.value.path()).read_text())
        check({r["sourceId"] for r in exported["records"]} == {"000123", "café", "cafe\u0301"}, "exact JSON IDs")

        control.set_input_files({"name": "bad.json", "mimeType": "application/json", "buffer": b'{"schema":"wrong","records":[]}'})
        page.locator("#resume-json-error").get_by_text("Unexpected evidence JSON schema", exact=False).wait_for()
        check(control.get_attribute("aria-invalid") == "true", "invalid file state")
        check(page.evaluate("document.activeElement.id") == "resume-json-error", "error focus")
        check(page.locator("#count").inner_text().startswith("3 records"), "bad schema leaves data")
        check(control.is_enabled(), "file control recovers")

        control.set_input_files({"name": "duplicate.json", "mimeType": "application/json", "buffer": fixture([record("X", "A"), record("X", "B")])})
        page.locator("#resume-json-error").get_by_text("duplicate source ID", exact=False).wait_for()
        check(page.locator("#count").inner_text().startswith("3 records"), "duplicate rejected")

        page.evaluate("""() => {const original=File.prototype.arrayBuffer;
            File.prototype.arrayBuffer=async function(){await new Promise(r=>setTimeout(r,450));return original.call(this)};}""")
        control.set_input_files({"name": "race.json", "mimeType": "application/json", "buffer": fixture([record("RACE", "Should not replace")])})
        check(control.is_disabled(), "input locked while reading")
        page.get_by_role("button", name="Remove record 000123").click()
        page.locator("#resume-json-error").get_by_text("Records changed while reading", exact=False).wait_for(timeout=4000)
        check(page.locator("#count").inner_text().startswith("2 records"), "stale import rejected")
        check(page.locator("#records").get_by_text("Should not replace").count() == 0, "no stale overwrite")
        check(control.is_enabled(), "input unlocked")
        check(not errors, "no JavaScript exceptions")
        check(not requests, "no network requests from injected DOM")
        page.set_viewport_size({"width": 320, "height": 700})
        check(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "320px reflow")
        page.evaluate("document.documentElement.style.zoom='2'")
        check(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "CSS zoom 200% reflow")
        browser.close()
    print(f"PASS: {checks} synthetic Chromium DOM-injected checks; HTTP/CSP/native AT not tested")


if __name__ == "__main__":
    run()
