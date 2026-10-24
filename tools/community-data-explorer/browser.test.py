"""Synthetic HTTP/CSP acceptance tests for the browser-local Community Data Explorer."""
import hashlib
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from functools import partial
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
CSV = ("source_id,geography,variable,series,period_start,period_end,estimate,moe\n"
       "00001,Place,B19013_001E,acs5,2015,2019,60000,1000\n"
       "00002,Place,B19013_001E,acs5,2020,2024,70000,1200\n")
checks = 0

def verify(condition, message):
    global checks
    assert condition, message
    checks += 1

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ROOT)))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = f"http://127.0.0.1:{server.server_port}/"

try:
    with sync_playwright() as pw:
        for engine_name in ("chromium", "firefox", "webkit"):
            browser = getattr(pw, engine_name).launch(headless=True)
            context = browser.new_context(viewport={"width": 320, "height": 720}, accept_downloads=True)
            page = context.new_page()
            errors = []
            outbound = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("request", lambda req: outbound.append(req.url) if not req.url.startswith(base) else None)
            response = page.goto(base, wait_until="networkidle")
            verify(response.status == 200, engine_name + ": HTTP 200")
            verify(page.locator("main").count() == 1, engine_name + ": main landmark")
            verify(page.locator("#status[role=status]").count() == 1, engine_name + ": status")
            page.locator("#csv").set_input_files({"name":"synthetic.csv","mimeType":"text/csv","buffer":CSV.encode("utf-8")})
            page.locator("#status").filter(has_text="2 records loaded locally").wait_for(timeout=15000)
            verify(page.locator("#compare").is_enabled(), engine_name + ": compare enabled")
            page.locator("#compare").click()
            verify("10000" in page.locator("#comparison").inner_text(), engine_name + ": comparison")
            with page.expect_download() as download_info:
                page.locator("#export").click()
            download = download_info.value
            evidence = json.loads(Path(download.path()).read_text())
            verify(evidence["records"][0]["source_id"] == "00001", engine_name + ": exact source ID")
            verify(evidence["comparison"]["difference"] == 10000, engine_name + ": exact difference")
            verify(evidence["source_file"]["sha256"] == hashlib.sha256(CSV.encode()).hexdigest(), engine_name + ": original SHA-256")
            verify(evidence["provenance_status"].endswith("not independently verified"), engine_name + ": provenance disclaimer")
            verify(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), engine_name + ": 320px reflow")
            bad = CSV.replace("00001,Place", "=1+1,Place")
            page.locator("#csv").set_input_files({"name":"unsafe.csv","mimeType":"text/csv","buffer":bad.encode()})
            page.locator("#error:not([hidden])").wait_for(timeout=15000)
            verify(page.locator("#error").evaluate("(el) => document.activeElement === el"), engine_name + ": error focus")
            verify(page.locator("#export").is_disabled(), engine_name + ": stale export blocked")
            verify(not outbound, engine_name + ": no outbound requests")
            verify(not errors, engine_name + ": no JavaScript page errors")
            context.close()
            browser.close()
            print(f"PASS: {engine_name} browser-local import, CSP, SHA-256, JSON, focus, reflow, privacy")
finally:
    server.shutdown()
    server.server_close()
print(f"PASS: {checks} HTTP-served cross-browser assertions")
