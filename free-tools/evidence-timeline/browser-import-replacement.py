"""Synthetic, real-browser regression for safe JSON replacement and error recovery.

Tests user confirmation, cancellation, stale filter recovery, keyboard focus,
exact source IDs, local-only requests, and exported data. No personal files.
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

def payload(rows):
    return json.dumps({"schema": "evidence-timeline-v1", "records": rows}, ensure_ascii=False).encode("utf-8")

def record(source_id, status="reported", claim="Synthetic source"):
    return {"sourceId": source_id, "date": "2026-10-25", "claim": claim,
            "status": status, "kind": "source", "group": ""}

def main():
    with serve() as url, sync_playwright() as playwright:
        origin = url.rsplit("/", 1)[0] + "/"
        for engine in ("chromium", "firefox", "webkit"):
            browser = getattr(playwright, engine).launch(headless=True)
            page = browser.new_page(viewport={"width": 320, "height": 700}, accept_downloads=True)
            errors, external, dialogs = [], [], []
            decision = {"accept": False}
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: external.append(request.url) if not request.url.startswith(origin) else None)
            def on_dialog(dialog):
                dialogs.append(dialog.message)
                if decision["accept"]:
                    dialog.accept()
                else:
                    dialog.dismiss()
            page.on("dialog", on_dialog)
            assert page.goto(url, wait_until="networkidle").status == 200
            page.locator("#sourceId").fill("000123")
            page.locator("#date").fill("2026-10-25")
            page.locator("#claim").fill("Synthetic existing evidence")
            page.get_by_role("button", name="Add record").click()
            assert page.locator("#records li").count() == 1
            page.locator("#review-filter").select_option("disputed")
            assert page.locator("#records li").count() == 0

            incoming = payload([
                record("000456", claim="Synthetic café — résumé"),
                record("000789", status="corroborated", claim="Synthetic second source")
            ])
            selector = page.locator("#resume-json")
            selector.set_input_files({"name": "synthetic.json", "mimeType": "application/json", "buffer": incoming})
            page.locator("#resume-json-status").filter(has_text="cancelled").wait_for()
            assert page.locator("#review-filter").input_value() == "disputed", (engine, "cancel changed filter")
            assert page.locator("#count").inner_text().startswith("Showing 0 of 1"), (engine, "cancel changed records")
            assert page.locator("#resume-json").is_enabled()
            assert selector.input_value() == ""
            assert len(dialogs) == 1 and "1 records" in dialogs[0] and "2 imported records" in dialogs[0], (engine, dialogs)
            assert "Synthetic existing evidence" not in dialogs[0] and "000123" not in dialogs[0], (engine, "private text in dialog")

            selector.set_input_files({"name": "broken.json", "mimeType": "application/json", "buffer": b"{invalid"})
            page.locator("#resume-json-error").wait_for(state="visible")
            assert selector.get_attribute("aria-invalid") == "true", (engine, "invalid input")
            assert page.evaluate("document.activeElement.id") == "resume-json-error", (engine, "error focus")
            assert page.locator("#count").inner_text().startswith("Showing 0 of 1"), (engine, "error changed records")

            decision["accept"] = True
            selector.set_input_files({"name": "synthetic.json", "mimeType": "application/json", "buffer": incoming})
            page.locator("#resume-json-status").filter(has_text="imported locally").wait_for()
            assert page.locator("#review-filter").input_value() == "all", (engine, "new records hidden by old filter")
            assert page.locator("#records li").count() == 2, (engine, "new records not shown")
            assert page.locator("#count").inner_text().startswith("2 records"), (engine, "incorrect count")
            assert page.evaluate("document.activeElement.id") == "count", (engine, "success focus")
            assert selector.get_attribute("aria-invalid") is None, (engine, "stale error")
            assert page.locator("#resume-json-error").is_hidden()
            assert selector.is_enabled() and selector.input_value() == ""
            with page.expect_download() as download:
                page.locator("#json").click()
            exported = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
            assert [r["sourceId"] for r in exported["records"]] == ["000456", "000789"], (engine, "exact identifiers")
            assert exported["records"][0]["claim"] == "Synthetic café — résumé", (engine, "Unicode changed")
            assert not errors and not external, (engine, errors, external)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (engine, "320px overflow")
            browser.close()
            print(f"PASS: {engine} cancelled/invalid/confirmed import, focus, exact IDs, privacy, reflow")
if __name__ == "__main__":
    main()
