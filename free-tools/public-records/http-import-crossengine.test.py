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

                        # The occupied workspace must not be replaced by a valid import.
                        import json
                        request = {'id':'REQ-00007','jurisdiction':'federal','agency':'Example agency',
                                   'stage':'draft','submittedOn':'','agencyTrackingId':'0000987',
                                   'description':'Synthetic request'}
                        event = {'id':'EV-00009','requestId':'REQ-00007','date':'2026-10-01',
                                 'kind':'note','sourceId':'SRC-00002','description':'Synthetic event'}
                        good = json.dumps({'version':1,'requests':[request],'events':[event]}).encode()
                        page.locator('#open-json').set_input_files({
                            'name':'synthetic.json','mimeType':'application/json','buffer':good})
                        page.locator('#status').get_by_text('Import not applied',exact=False).wait_for()
                        self.assertIn('synthetic-req-001',page.locator('#requests').inner_text())
                        self.assertNotIn('REQ-00007',page.locator('#requests').inner_text())

                        # In a separate empty page, malformed escaped duplicate keys fail closed,
                        # followed by a valid import with exact source and leading-zero IDs.
                        imported = browser.new_page(accept_downloads=True,viewport={'width':320,'height':800})
                        try:
                            self.assertEqual(imported.goto(url,wait_until='networkidle').status,200)
                            bad = b'{"version":1,"requests":[],"events":[],"\\u0076ersion":1}'
                            imported.locator('#open-json').set_input_files({
                                'name':'bad.json','mimeType':'application/json','buffer':bad})
                            imported.locator('#status').get_by_text('Import rejected',exact=False).wait_for()
                            self.assertIn('Duplicate JSON object key',imported.locator('#status').inner_text())
                            self.assertIn('No requests yet',imported.locator('#requests').inner_text())
                            imported.locator('#open-json').set_input_files({
                                'name':'synthetic.json','mimeType':'application/json','buffer':good})
                            imported.locator('#status').get_by_text('Imported 1 requests and 1 events',exact=False).wait_for()
                            self.assertIn('REQ-00007',imported.locator('#requests').inner_text())
                            chronology = imported.locator('#events').inner_text()
                            self.assertIn('Event EV-00009',chronology)
                            self.assertIn('Request REQ-00007',chronology)
                            self.assertIn('source SRC-00002',chronology)
                            imported.evaluate("document.documentElement.style.fontSize='64px'")
                            geometry = imported.evaluate("""() => ({
                                viewport: innerWidth,
                                document: document.documentElement.scrollWidth,
                                suspects: [...document.querySelectorAll('body *')]
                                    .map(e => ({
                                        tag: e.tagName, id: e.id,
                                        right: Math.round(e.getBoundingClientRect().right),
                                        width: Math.round(e.getBoundingClientRect().width),
                                        scroll: e.scrollWidth, client: e.clientWidth
                                    }))
                                    .filter(e => e.right > innerWidth + 1 ||
                                        e.scroll > e.client + 1)
                                    .slice(0, 15)
                            })""")
                            self.assertLessEqual(
                                geometry['document'], geometry['viewport'],
                                '400% root-font scaling overflow: ' + str(geometry))
                        finally:
                            imported.close()
                    finally:
                        page.close()
            finally:
                browser.close()

if __name__ == '__main__':
    unittest.main()
