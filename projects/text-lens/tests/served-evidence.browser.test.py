"""Real HTTP/CSP and local evidence-export regression for Text Lens.

Uses only synthetic prose. No external resources, account, or real transcripts.
"""
import base64
import csv
import hashlib
import io
import json
import os
import re
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "text-lens.html").read_text(encoding="utf-8")
SCRIPTS = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", HTML, re.I | re.S)
assert len(SCRIPTS) == 4, "Review the CSP hash list if inline scripts change"
HASHES = " ".join(
    "'sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii") + "'"
    for script in SCRIPTS
)
POLICY = (
    "default-src 'none'; script-src 'self' " + HASHES +
    "; style-src 'unsafe-inline'; connect-src 'none'; img-src 'self' data:; "
    "font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)
SYNTHETIC = "The library was wonderful. The staff were helpful and kind."


class LocalHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Content-Security-Policy", POLICY)
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, *_args):
        pass


@contextmanager
def serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def download_bytes(page, selector):
    with page.expect_download(timeout=8000) as info:
        page.locator(selector).click()
    return Path(info.value.path()).read_bytes()


def no_download(page, selector):
    try:
        with page.expect_download(timeout=700):
            page.locator(selector).click()
    except PlaywrightTimeoutError:
        return
    raise AssertionError("Unsafe evidence unexpectedly exported as CSV")


def main():
    engine = os.environ.get("FT11_BROWSER", "chromium")
    checks = 0
    with serve() as origin, sync_playwright() as pw:
        browser = getattr(pw, engine).launch(headless=True)
        page = browser.new_page(viewport={"width": 375, "height": 812}, accept_downloads=True)
        requests, errors = [], []
        page.on("request", lambda req: requests.append(req.url))
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            response = page.goto(origin + "/text-lens.html", wait_until="domcontentloaded")
            assert response.status == 200
            checks += 1
            assert response.headers["content-security-policy"] == POLICY
            checks += 1
            expect(page.locator("#status")).to_contain_text("Paste text", timeout=10000)
            checks += 1
            assert page.evaluate("""async () => {
                try { await fetch('/text-lens.html'); return false; }
                catch (_) { return true; }
            }""")
            checks += 1
            expect(page.locator("#cueCsv")).to_be_disabled()
            checks += 1

            page.locator("#fileA").set_input_files({
                "name": "=1+1.txt", "mimeType": "text/plain",
                "buffer": SYNTHETIC.encode("utf-8")
            })
            expect(page.locator("#cueCsv")).to_be_enabled(timeout=10000)
            checks += 1
            expect(page.locator("#fileMetaA")).to_contain_text("=1+1.txt")
            checks += 1
            no_download(page, "#cueCsv")
            checks += 1
            expect(page.locator("#status")).to_contain_text("CSV export blocked")
            checks += 1
            assert page.evaluate("document.activeElement.id") == "status"
            checks += 1

            unsafe_json = json.loads(download_bytes(page, "#cueJson").decode("utf-8"))
            assert unsafe_json["export_type"] == "filtered-evidence"
            checks += 1
            assert unsafe_json["rows"] and all(row["source"] == "=1+1.txt" for row in unsafe_json["rows"])
            checks += 1
            assert all(row["passage"] in SYNTHETIC for row in unsafe_json["rows"])
            checks += 1

            # General analysis-table exports also contain untrusted filenames.
            no_download(page, "#downloadcsv")
            checks += 1
            expect(page.locator("#status")).to_contain_text("CSV export blocked")
            checks += 1
            assert page.evaluate("document.activeElement.id") == "status"
            checks += 1
            unsafe_tables = json.loads(download_bytes(page, "#downloadTablesJson").decode("utf-8"))
            assert unsafe_tables["export_type"] == "analysis-tables"
            checks += 1
            assert unsafe_tables["columns"][:3] == ["section", "text", "item"]
            checks += 1
            assert any(row[0] == "document_summary" and row[2] == "=1+1.txt"
                       for row in unsafe_tables["rows"])
            checks += 1

            page.locator("#fileA").set_input_files({
                "name": "archive.txt", "mimeType": "text/plain",
                "buffer": SYNTHETIC.encode("utf-8")
            })
            expect(page.locator("#fileMetaA")).to_contain_text("archive.txt")
            checks += 1
            expect(page.locator("#cueCsv")).to_be_enabled(timeout=10000)
            checks += 1
            safe_csv = download_bytes(page, "#cueCsv").decode("utf-8-sig")
            table = list(csv.reader(io.StringIO(safe_csv)))
            assert len(table) > 1 and table[0][1] == "source_file"
            checks += 1
            assert all(row[1] == "archive.txt" for row in table[1:])
            checks += 1
            assert all("=1+1.txt" not in row for row in table[1:])
            checks += 1
            safe_tables = download_bytes(page, "#downloadcsv").decode("utf-8-sig")
            assert any(row[0] == "document_summary" and row[2] == "archive.txt"
                       for row in csv.reader(io.StringIO(safe_tables)))
            checks += 1
            safe_tables_json = json.loads(download_bytes(page, "#downloadTablesJson").decode("utf-8"))
            assert "non-finite metrics" in safe_tables_json["source_note"]
            checks += 1
            assert all(value is not None for row in safe_tables_json["rows"] for value in row)
            checks += 1
            assert any(row[0] == "document_summary" and row[2] == "archive.txt"
                       for row in safe_tables_json["rows"])
            checks += 1


            # Fault-inject real browser download boundaries after a safe local import.
            # These tests exercise the page event handler under the served CSP,
            # not merely a copied function in a synthetic JavaScript sandbox.
            for selector, label in [("#downloadcsv", "CSV"), ("#downloadTablesJson", "JSON")]:
                for fault in ("url", "append", "click"):
                    page.evaluate("""fault => {
                        const original = {
                            create: URL.createObjectURL,
                            revoke: URL.revokeObjectURL,
                            append: document.body.appendChild,
                            click: HTMLAnchorElement.prototype.click
                        };
                        const state = {created: [], revoked: [],
                            initialLinks: document.querySelectorAll('a[download]').length};
                        URL.createObjectURL = function(blob) {
                            if (fault === 'url') throw new Error('synthetic URL refusal');
                            const url = original.create.call(URL, blob);
                            state.created.push(url);
                            return url;
                        };
                        URL.revokeObjectURL = function(url) {
                            // Ignore earlier successful exports' delayed revocations.
                            if (state.created.includes(url)) state.revoked.push(url);
                            return original.revoke.call(URL, url);
                        };
                        document.body.appendChild = function(node) {
                            if (fault === 'append' && node.tagName === 'A' && node.download)
                                throw new Error('synthetic append refusal');
                            return original.append.call(this, node);
                        };
                        HTMLAnchorElement.prototype.click = function() {
                            if (fault === 'click' && this.download)
                                throw new Error('synthetic click refusal');
                            return original.click.call(this);
                        };
                        window.__ft11Fault = {state, restore() {
                            URL.createObjectURL = original.create;
                            URL.revokeObjectURL = original.revoke;
                            document.body.appendChild = original.append;
                            HTMLAnchorElement.prototype.click = original.click;
                            return {...state,
                                remainingLinks: document.querySelectorAll('a[download]').length};
                        }};
                    }""", fault)
                    try:
                        no_download(page, selector)
                        checks += 1
                        expect(page.locator("#status")).to_contain_text(
                            label + " download could not be started")
                        checks += 1
                        assert page.evaluate("document.activeElement.id") == "status"
                        checks += 1
                        assert "archive.txt" not in page.locator("#status").inner_text()
                        checks += 1
                    finally:
                        state = page.evaluate("window.__ft11Fault.restore()")
                    assert state["remainingLinks"] == state["initialLinks"], state
                    checks += 1
                    expected = 0 if fault == "url" else 1
                    assert len(state["created"]) == expected, state
                    assert state["revoked"] == state["created"], state
                    checks += 1

                # A failure must not poison the next successful download.
                if label == "CSV":
                    recovered = download_bytes(page, selector).decode("utf-8-sig")
                    assert any(row[0] == "document_summary" and row[2] == "archive.txt"
                               for row in csv.reader(io.StringIO(recovered)))
                else:
                    recovered = json.loads(download_bytes(page, selector).decode("utf-8"))
                    assert any(row[0] == "document_summary" and row[2] == "archive.txt"
                               for row in recovered["rows"])
                checks += 1

            page.locator("#a").fill("An unrelated sentence with no evaluative cue.")
            expect(page.locator("#cueCsv")).to_be_disabled(timeout=10000)
            checks += 1
            assert "Manual edits detected" in page.locator("#fileMetaA").inner_text()
            checks += 1
            cleared = json.loads(download_bytes(page, "#cueJson").decode("utf-8"))
            assert cleared["rows"] == []
            checks += 1

            # Invalid local files cannot overwrite the existing manual corpus.
            prior_text = page.locator("#a").input_value()
            page.locator("#fileA").set_input_files({
                "name": "malformed.txt", "mimeType": "text/plain",
                "buffer": b"\xc3\x28"
            })
            expect(page.locator("#status")).to_contain_text("Invalid UTF-8", timeout=10000)
            checks += 1
            assert page.locator("#a").input_value() == prior_text
            checks += 1
            assert page.evaluate("document.activeElement.id") == "status"
            checks += 1

            page.locator("#fileA").set_input_files({
                "name": "too-large.txt", "mimeType": "text/plain",
                "buffer": b"x" * 5_000_001
            })
            expect(page.locator("#status")).to_contain_text("byte local limit", timeout=10000)
            checks += 1
            assert page.locator("#a").input_value() == prior_text
            checks += 1

            # A valid BOM-prefixed Unicode file can be imported after errors.
            page.locator("#fileA").set_input_files({
                "name": "café.md", "mimeType": "text/markdown",
                "buffer": b"\xef\xbb\xbf" + "Café 東京 😀".encode("utf-8")
            })
            expect(page.locator("#a")).to_have_value("Café 東京 😀", timeout=10000)
            checks += 1
            expect(page.locator("#fileMetaA")).to_contain_text("café.md")
            checks += 1

            page.locator("#fileA").set_input_files({
                "name": "binary.csv", "mimeType": "text/csv",
                "buffer": b"alpha\x00beta"
            })
            expect(page.locator("#status")).to_contain_text("NUL", timeout=10000)
            checks += 1
            assert page.locator("#a").input_value() == "Café 東京 😀"
            checks += 1

            # A cross-component import must update the actual analyzed text, not just its source label.
            # The earlier implementation silently analyzed the previous textarea contents.
            def dispatch_import(key, name, text, size=None):
                detail = {
                    "key": key, "name": name,
                    "size": len(text.encode("utf-8")) if size is None else size,
                    "lastModified": 0, "text": text
                }
                page.evaluate("""detail => {
                    document.querySelector('#leh-text-lens-app').dispatchEvent(
                        new CustomEvent('text-lens:import', {detail})
                    );
                }""", detail)

            imported_a = "The museum was wonderful. The guides were helpful and kind."
            imported_b = "The hallway was terrible and the signs were confusing."
            page.locator("#a").fill("The previous corpus was entirely different.")
            dispatch_import("a", "0001-東京.md", imported_a)
            expect(page.locator("#a")).to_have_value(imported_a)
            checks += 1
            expect(page.locator("#fileMetaA")).to_contain_text("0001-東京.md")
            checks += 1
            analysis_a = json.loads(download_bytes(page, "#download").decode("utf-8"))
            assert analysis_a["source_files"]["text_a"] == ["0001-東京.md"]
            checks += 1
            assert (analysis_a["text_a"]["counts"]["words"] ==
                    analysis_a["document_profiles"]["text_a"][0]["analysis"]["counts"]["words"])
            checks += 1
            assert analysis_a["text_a"]["counts"]["words"] > 5
            checks += 1
            cues_a = json.loads(download_bytes(page, "#cueJson").decode("utf-8"))
            assert cues_a["rows"] and all(row["source"] == "0001-東京.md" for row in cues_a["rows"])
            checks += 1

            page.locator("#cmp").check()
            dispatch_import("b", "0002-résumé.txt", imported_b)
            expect(page.locator("#b")).to_have_value(imported_b)
            checks += 1
            assert page.locator("#a").input_value() == imported_a
            checks += 1
            analysis_b = json.loads(download_bytes(page, "#download").decode("utf-8"))
            assert analysis_b["source_files"]["text_b"] == ["0002-résumé.txt"]
            checks += 1
            assert (analysis_b["text_b"]["counts"]["words"] ==
                    analysis_b["document_profiles"]["text_b"][0]["analysis"]["counts"]["words"])
            checks += 1

            dispatch_import("a", "invalid.txt", "rejected", size=-1)
            expect(page.locator("#status")).to_contain_text("Import rejected")
            checks += 1
            assert page.locator("#a").input_value() == imported_a
            checks += 1
            assert page.evaluate("document.activeElement.id") == "status"
            checks += 1

            # Untrusted cross-tool events must not spoof UTF-8 size or display a
            # misleading filename. Rejections retain the last valid source.
            for bad_name, bad_size, reason in [
                ("reverse\\u202Etxt.md", len(imported_a.encode("utf-8")), "Source name"),
                ("line\\nname.md", len(imported_a.encode("utf-8")), "Source name"),
                ("0001-東京.md", 1, "byte size does not match"),
            ]:
                bad_name = bad_name.replace("\\\\u202E", chr(0x202E)).replace("\\\\n", "\\n")
                dispatch_import("a", bad_name, imported_a, size=bad_size)
                expect(page.locator("#status")).to_contain_text(reason)
                checks += 1
                assert page.locator("#a").input_value() == imported_a
                checks += 1
                assert page.locator("#fileMetaA").inner_text().endswith("0001-東京.md · local text")
                checks += 1
                assert page.evaluate("document.activeElement.id") == "status"
                checks += 1

            recovered_text = "Café 東京 😀 and the museum guides were wonderful."
            dispatch_import("a", "0007-Café-東京.md", recovered_text)
            expect(page.locator("#a")).to_have_value(recovered_text)
            checks += 1
            expect(page.locator("#fileMetaA")).to_contain_text("0007-Café-東京.md")
            checks += 1
            recovered_json = json.loads(download_bytes(page, "#download").decode("utf-8"))
            assert recovered_json["source_files"]["text_a"] == ["0007-Café-東京.md"]
            checks += 1

            assert not errors, errors
            checks += 1
            assert requests and all(url.startswith(origin + "/") for url in requests), requests
            checks += 1
        finally:
            browser.close()
    print(f"PASS: {checks} FT-11 {engine} HTTP/CSP/unsafe-CSV/exact-JSON/focus/recovery/stale-source checks")


if __name__ == "__main__":
    main()
