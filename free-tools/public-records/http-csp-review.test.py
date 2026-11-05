"""HTTP-served CSP smoke test for the browser-local public-records workspace.

Run with FT09_BROWSER=chromium|firefox|webkit after installing Playwright.
Uses only synthetic records and an ephemeral loopback HTTP server.
"""
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import os
import unittest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent

@contextmanager
def serve():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:%d/index.html' % server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

class HttpCspReview(unittest.TestCase):
    def test_local_modules_form_download_and_network_policy(self):
        engine = os.environ.get('FT09_BROWSER', 'chromium')
        if engine not in ('chromium', 'firefox', 'webkit'):
            raise ValueError('Unsupported browser engine')
        with sync_playwright() as pw:
            browser = getattr(pw, engine).launch(headless=True)
            try:
                with serve() as url:
                    page = browser.new_page(accept_downloads=True)
                    try:
                        requested = []
                        page.on('request', lambda req: requested.append(req.url))
                        response = page.goto(url, wait_until='networkidle')
                        self.assertEqual(response.status, 200)
                        page.locator('#request-form input[name="id"]').fill('synthetic-req-001')
                        page.locator('#request-form input[name="agency"]').fill('Example agency')
                        page.locator('#request-form textarea[name="description"]').fill('Synthetic request')
                        page.locator('#request-form button[type="submit"]').click()
                        self.assertIn('synthetic-req-001', page.locator('#requests').inner_text())
                        network_allowed = page.evaluate("""async () => {
                            try { const result = await fetch(location.href); return result.ok; }
                            catch (error) { return false; }
                        }""")
                        self.assertFalse(network_allowed, 'connect-src none must block fetch')
                        with page.expect_download() as download:
                            page.locator('#save-json').click()
                        self.assertTrue(download.value.suggested_filename.endswith('.json'))
                        self.assertTrue(all(item.startswith(url.rsplit('/', 1)[0]) for item in requested))
                    finally:
                        page.close()
            finally:
                browser.close()

if __name__ == '__main__':
    unittest.main()
