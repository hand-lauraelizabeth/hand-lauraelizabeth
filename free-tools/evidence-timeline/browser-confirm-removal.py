"""Synthetic browser regression for confirmation before local evidence deletion.

Tests native keyboard activation, cancel/confirm semantics, export fidelity,
focus recovery, 320px reflow, and local-only requests in three engines.
No personal data and no production site access.
"""
import json
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent

@contextmanager
def serve():
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ROOT)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/index.html"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

def add(page, source_id, claim):
    page.locator("#sourceId").fill(source_id)
    page.locator("#date").fill("2026-10-25")
    page.locator("#claim").fill(claim)
    page.get_by_role("button", name="Add record").click()

def exported(page):
    with page.expect_download() as download:
        page.get_by_role("button", name="Export exact JSON").click()
    return json.loads(download.value.path().read_text(encoding="utf-8"))

def main():
    with serve() as url, sync_playwright() as playwright:
        origin = url.rsplit("/", 1)[0] + "/"
        for engine in ("chromium", "firefox", "webkit"):
            browser = getattr(playwright, engine).launch(headless=True)
            page = browser.new_page(viewport={"width": 320, "height": 700}, accept_downloads=True)
            errors, external, dialogs = [], [], []
            accept = {"value": False}
            page.on("pageerror", lambda err: errors.append(str(err)))
            page.on("request", lambda req: external.append(req.url) if not req.url.startswith(origin) else None)
            def dialog_handler(dialog):
                dialogs.append(dialog.message)
                if accept["value"]:
                    dialog.accept()
                else:
                    dialog.dismiss()
            page.on("dialog", dialog_handler)
            assert page.goto(url, wait_until="networkidle").status == 200
            add(page, "000123", "Synthetic café — résumé")
            add(page, "000456", "Synthetic second source")
            assert page.locator("#records li").count() == 2
            before = exported(page)
            assert [r["sourceId"] for r in before["records"]] == ["000123", "000456"], (engine, before)
            assert before["records"][0]["claim"] == "Synthetic café — résumé"

            button = page.get_by_role("button", name="Remove record 000123")
            button.focus()
            page.keyboard.press("Enter")
            assert len(dialogs) == 1, (engine, "no confirmation")
            assert "000123" not in dialogs[0] and "café" not in dialogs[0], (engine, "private data in dialog")
            assert "cannot be undone" in dialogs[0].lower(), (engine, dialogs)
            assert page.locator("#records li").count() == 2, (engine, "cancel deleted a record")
            assert page.evaluate("document.activeElement.getAttribute('aria-label')") == "Remove record 000123", (engine, "cancel focus")
            assert exported(page) == before, (engine, "cancel altered exact export")

            accept["value"] = True
            button = page.get_by_role("button", name="Remove record 000123")
            button.focus()
            page.keyboard.press("Enter")
            assert len(dialogs) == 2, (engine, "confirmation not repeated")
            assert page.locator("#records li").count() == 1, (engine, "confirmation did not delete")
            assert page.evaluate("document.activeElement.id") == "count", (engine, "focus not recovered")
            assert page.locator("#count").get_attribute("role") == "status", (engine, "status semantics")
            assert page.locator("#count").inner_text().startswith("1 record"), (engine, "count not updated")
            after = exported(page)
            assert [r["sourceId"] for r in after["records"]] == ["000456"], (engine, after)
            assert before["records"][1] == after["records"][0], (engine, "remaining source mutated")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (engine, "320px overflow")
            assert not errors and not external, (engine, errors, external)
            browser.close()
            print(f"PASS: {engine} 18 synthetic deletion confirmation and export checks")

if __name__ == "__main__":
    main()
