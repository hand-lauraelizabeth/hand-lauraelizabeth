"""Hosted-preview-equivalent Chromium interaction and accessibility smoke tests."""
import pathlib
import functools
import http.server
import threading
from playwright.sync_api import sync_playwright

DIRECTORY = pathlib.Path(__file__).resolve().parent

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def main():
    handler = functools.partial(QuietHandler, directory=str(DIRECTORY))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/admissions-evidence-review-preview.html"
    try:
      with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={"width":390,"height":844})
        errors=[]
        page.on("pageerror",lambda e: errors.append(str(e)))
        response = page.goto(url)
        page.wait_for_load_state("load")
        # Fail with actionable HTTP and JavaScript diagnostics rather than an opaque selector timeout.
        if not response or response.status != 200:
            raise AssertionError(f"Preview HTTP status: {response.status if response else 'no response'} at {url}")
        try:
            page.locator("#check-cycle").wait_for(state="attached", timeout=5000)
        except Exception as exc:
            raise AssertionError(f"Admissions checklist did not initialize; JS errors={errors}; document title={page.title()!r}; script count={page.locator('script').count()}; checks markup={page.locator('#checks').inner_html()!r}") from exc
        assert page.get_by_role("heading",name="College + Career Matcher: admissions evidence").is_visible()
        page.locator("#check-cycle").check()
        assert "1 of 3" in page.locator("#check-status").inner_text()
        page.locator("#route").select_option("accelerated")
        assert "0 of 3" in page.locator("#check-status").inner_text()
        page.locator("#check-prerequisites").check()
        page.locator("#route").select_option("generic")
        assert page.locator("#check-cycle").is_checked()
        page.locator("#clear-all-checks").click()
        page.locator("#route").select_option("accelerated")
        assert not page.locator("#check-prerequisites").is_checked()
        page.locator("#route").select_option("rn")
        with page.expect_download() as download:
            page.locator("#download-evidence").click()
        assert "rn-nursing-pathway" in download.value.suggested_filename
        assert not errors,errors
        # Storage-disabled behavior: both sessionStorage methods throw.
        page.add_init_script("""() => {
          Object.defineProperty(window,'sessionStorage',{get(){throw Error('disabled')}});
        }""")
        page.reload()
        page.locator("#check-cycle").check()
        assert "1 of 3" in page.locator("#check-status").inner_text()
        assert "unavailable" in page.locator("#check-status").inner_text()
        page.locator("#clear-all-checks").click()
        assert "0 of 3" in page.locator("#check-status").inner_text()
        assert not errors,errors
        browser.close()
    finally:
      server.shutdown()
      server.server_close()
    print("PASS: pathway state, privacy clear, download, storage-disabled fallback, mobile Chromium")

if __name__=="__main__":main()
