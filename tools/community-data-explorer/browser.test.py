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
            decimal_csv = ("source_id,geography,variable,series,period_start,period_end,estimate,moe\n"
                           "00001,Place,B01002_001E,acs5,2015,2019,37.4,0.3\n"
                           "00002,Place,B01002_001E,acs5,2020,2024,38.1,0.4\n")
            page.locator("#csv").set_input_files({"name":"synthetic-median-age.csv","mimeType":"text/csv","buffer":decimal_csv.encode()})
            page.locator("#status").filter(has_text="2 records loaded locally").wait_for(timeout=15000)
            page.locator("#compare").click()
            verify("0.7" in page.locator("#comparison").inner_text(), engine_name + ": exact decimal UI")
            with page.expect_download() as decimal_download:
                page.locator("#export").click()
            decimal_evidence = json.loads(Path(decimal_download.value.path()).read_text())
            verify(decimal_evidence["comparison"]["difference_exact"] == "0.7", engine_name + ": exact decimal evidence")
            verify(decimal_evidence["records"][0]["moe_raw"] == "0.3", engine_name + ": decimal MOE provenance")
            verify(decimal_evidence["records"][0]["source_id"] == "00001", engine_name + ": decimal source ID")
            annotated_csv = ("source_id,geography,variable,series,period_start,period_end,estimate,moe\n"
                             "00001,Place,B01002_001E,acs5,2015,2019,37.4,-555555555.00\n"
                             "00002,Place,B01002_001E,acs5,2020,2024,38.1,0.4\n")
            page.locator("#csv").set_input_files({"name":"synthetic-annotated.csv","mimeType":"text/csv","buffer":annotated_csv.encode()})
            page.locator("#status").filter(has_text="2 records loaded locally").wait_for(timeout=15000)
            verify("controlled" in page.locator("#records").inner_text().lower(), engine_name + ": controlled MOE visibly annotated")
            page.locator("#compare").click()
            verify("not a numeric zero" in page.locator("#comparison").inner_text(), engine_name + ": nonzero controlled-MOE caution")
            with page.expect_download() as annotated_download:
                page.locator("#export").click()
            annotated_evidence = json.loads(Path(annotated_download.value.path()).read_text())
            verify(annotated_evidence["records"][0]["moe_raw"] == "-555555555.00", engine_name + ": raw MOE annotation")
            verify(annotated_evidence["records"][0]["moe_status"] == "controlled_moe", engine_name + ": explicit MOE status")
            verify(annotated_evidence["records"][0]["moe"] is None, engine_name + ": annotated MOE never numeric zero")
            verify(annotated_evidence["comparison"]["difference_exact"] == "0.7", engine_name + ": arithmetic preserved with annotated MOE")
            # A second valid import must be explicitly confirmed; cancelling is lossless.
            replacement_csv = ("source_id,geography,variable,series,period_start,period_end,estimate,moe\\n"
                               "00999,Other Place,B01002_001E,acs5,2015,2019,40.0,0.2\\n"
                               "01000,Other Place,B01002_001E,acs5,2020,2024,42.0,0.3\\n")
            # The string above uses literal escape sequences for predictable synthetic bytes.
            replacement_csv = replacement_csv.replace("\\\\n", "\\n")
            dialogs = []
            def dismiss_replacement(dialog):
                dialogs.append(dialog.message)
                dialog.dismiss()
            page.once("dialog", dismiss_replacement)
            page.locator("#csv").set_input_files({"name":"replacement.csv","mimeType":"text/csv","buffer":replacement_csv.encode()})
            page.locator("#status").filter(has_text="Replacement cancelled").wait_for(timeout=15000)
            verify(len(dialogs) == 1 and "Replace" in dialogs[0], engine_name + ": replacement confirmation offered")
            verify("controlled" in page.locator("#records").inner_text().lower(), engine_name + ": cancel preserves original preview")
            verify("0.7" in page.locator("#comparison").inner_text(), engine_name + ": cancel preserves comparison")
            with page.expect_download() as cancelled_export:
                page.locator("#export").click()
            verify(json.loads(Path(cancelled_export.value.path()).read_text()) == annotated_evidence,
                   engine_name + ": cancelled replacement preserves exact JSON")

            # An invalid import must preserve the previous workspace and show a focusable error.
            bad = CSV.replace("00001,Place", "=1+1,Place")
            page.locator("#csv").set_input_files({"name":"unsafe.csv","mimeType":"text/csv","buffer":bad.encode()})
            page.locator("#error:not([hidden])").wait_for(timeout=15000)
            verify(page.locator("#error").evaluate("(el) => document.activeElement === el"), engine_name + ": invalid import error focus")
            verify(page.locator("#export").is_enabled(), engine_name + ": invalid import retains export")
            verify("controlled" in page.locator("#records").inner_text().lower(), engine_name + ": invalid import preserves records")
            with page.expect_download() as invalid_export:
                page.locator("#export").click()
            verify(json.loads(Path(invalid_export.value.path()).read_text()) == annotated_evidence,
                   engine_name + ": invalid import preserves exact JSON")

            # Confirmed replacement removes only the old in-memory workspace and its stale comparison.
            accepted_dialogs = []
            def accept_replacement(dialog):
                accepted_dialogs.append(dialog.message)
                dialog.accept()
            page.once("dialog", accept_replacement)
            page.locator("#csv").set_input_files({"name":"replacement.csv","mimeType":"text/csv","buffer":replacement_csv.encode()})
            page.locator("#status").filter(has_text="2 records loaded locally").wait_for(timeout=15000)
            verify(len(accepted_dialogs) == 1, engine_name + ": accepted replacement confirmation")
            verify("00999" in page.locator("#records").inner_text() and "00001" not in page.locator("#records").inner_text(),
                   engine_name + ": accepted replacement shows only new source IDs")
            verify(not page.locator("#comparison").inner_text().strip(), engine_name + ": accepted replacement clears stale comparison")
            with page.expect_download() as replaced_export:
                page.locator("#export").click()
            replaced = json.loads(Path(replaced_export.value.path()).read_text())
            verify([r["source_id"] for r in replaced["records"]] == ["00999", "01000"],
                   engine_name + ": accepted replacement JSON source IDs")
            verify(replaced["comparison"] is None and replaced["source_file"]["sha256"] == hashlib.sha256(replacement_csv.encode()).hexdigest(),
                   engine_name + ": replacement JSON hash and comparison reset")
            verify(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), engine_name + ": replacement 320px reflow")
            verify(not outbound, engine_name + ": no outbound requests")
            verify(not errors, engine_name + ": no JavaScript page errors")
            context.close()
            browser.close()
            print(f"PASS: {engine_name} browser-local import, CSP, SHA-256, JSON, focus, reflow, privacy")
finally:
    server.shutdown()
    server.server_close()
print(f"PASS: {checks} HTTP-served cross-browser assertions")
