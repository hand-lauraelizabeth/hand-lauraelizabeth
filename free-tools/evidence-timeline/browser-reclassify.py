"""Synthetic HTTP-served three-engine status reclassification and keyboard recovery."""
import json
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent

@contextmanager
def serve():
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    worker=Thread(target=server.serve_forever,daemon=True)
    worker.start()
    try: yield f'http://127.0.0.1:{server.server_port}/index.html'
    finally:
        server.shutdown();server.server_close();worker.join(timeout=5)

def add(page,source_id,claim):
    page.locator('#sourceId').fill(source_id)
    page.locator('#date').fill('2026-10-25')
    page.locator('#claim').fill(claim)
    page.get_by_role('button',name='Add record').click()

def export(page):
    with page.expect_download() as download:
        page.get_by_role('button',name='Export exact JSON').click()
    return json.loads(download.value.path().read_text(encoding='utf-8'))

def main():
    with serve() as url, sync_playwright() as p:
        origin=url.rsplit('/',1)[0]+'/'
        for engine in ('chromium','firefox','webkit'):
            browser=getattr(p,engine).launch(headless=True)
            page=browser.new_page(viewport={'width':320,'height':700},accept_downloads=True)
            errors=[];external=[]
            page.on('pageerror',lambda e: errors.append(str(e)))
            page.on('request',lambda req: external.append(req.url) if not req.url.startswith(origin) else None)
            assert page.goto(url,wait_until='networkidle').status==200
            add(page,'000123','Synthetic café — résumé')
            add(page,'000456','Synthetic second')
            original=export(page)
            assert [r['sourceId'] for r in original['records']]==['000123','000456']
            assert [r['status'] for r in original['records']]==['reported','reported']
            page.locator('#review-filter').select_option('reported')
            assert page.locator('#records li').count()==2
            status=page.get_by_role('combobox',name='Review status for record 000123')
            status.focus()
            status.select_option('corroborated')
            assert page.locator('#review-filter').input_value()=='all',engine
            assert page.locator('#records li').count()==2,engine
            assert page.evaluate('document.activeElement.getAttribute("aria-label")')=='Review status for record 000123',engine
            assert page.locator('#change-status-message').get_attribute('role')=='status'
            assert 'All statuses are now shown' in page.locator('#change-status-message').inner_text()
            assert 'Corroborated: 1' in page.locator('#review-summary').inner_text()
            changed=export(page)
            assert changed['records'][0]['sourceId']=='000123' and changed['records'][0]['status']=='corroborated'
            assert changed['records'][0]['claim']=='Synthetic café — résumé'
            assert changed['records'][1]==original['records'][1],engine
            assert page.locator('#csv').is_enabled(),engine
            page.get_by_role('combobox',name='Review status for record 000123').select_option('disputed')
            assert export(page)['records'][0]['status']=='disputed',engine
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),engine
            assert not errors and not external,(engine,errors,external)
            browser.close()
            print(f'PASS: {engine} 18 synthetic status, focus, export and local-only checks')

if __name__=='__main__': main()
