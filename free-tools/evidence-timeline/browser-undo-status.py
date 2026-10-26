"""Synthetic HTTP-served cross-browser acceptance for one-step status undo."""
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
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try: yield f'http://127.0.0.1:{server.server_port}/index.html'
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)

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
    with serve() as url, sync_playwright() as playwright:
        origin=url.rsplit('/',1)[0]+'/'
        for engine in ('chromium','firefox','webkit'):
            browser=getattr(playwright,engine).launch(headless=True)
            page=browser.new_page(viewport={'width':320,'height':700},accept_downloads=True)
            errors=[];external=[]
            page.on('pageerror',lambda error: errors.append(str(error)))
            page.on('request',lambda request: external.append(request.url) if not request.url.startswith(origin) else None)
            assert page.goto(url,wait_until='networkidle').status==200
            add(page,'000123','Synthetic café — résumé')
            add(page,'000456','Synthetic unrelated')
            before=export(page)
            undo=page.get_by_role('button',name='Undo last review status change')
            assert undo.is_hidden(),(engine,'undo initially hidden')
            page.locator('#review-filter').select_option('reported')
            status=page.get_by_role('combobox',name='Review status for record 000123')
            status.select_option('disputed')
            assert undo.is_visible() and undo.is_enabled(),(engine,'undo offered')
            assert page.locator('#review-filter').input_value()=='all'
            assert export(page)['records'][0]['status']=='disputed'
            undo.focus()
            page.keyboard.press('Enter')
            assert undo.is_hidden(),(engine,'single-use undo')
            assert page.evaluate('document.activeElement.getAttribute("aria-label")')=='Review status for record 000123'
            assert export(page)==before,(engine,'exact original export restored')
            assert 'undone' in page.locator('#change-status-message').inner_text()
            page.get_by_role('combobox',name='Review status for record 000123').select_option('corroborated')
            page.get_by_role('combobox',name='Review status for record 000456').select_option('disputed')
            undo.click()
            after=export(page)
            assert after['records'][0]['status']=='corroborated',(engine,'only latest change undoable')
            assert after['records'][1]['status']=='reported',(engine,'latest undone')
            page.get_by_role('combobox',name='Review status for record 000123').select_option('unresolved')
            assert undo.is_visible()
            add(page,'000789','Synthetic third')
            assert undo.is_hidden(),(engine,'add invalidates undo')
            after_add=export(page)
            assert after_add['records'][0]['claim']=='Synthetic café — résumé'
            assert after_add['records'][0]['sourceId']=='000123'
            assert after_add['records'][0]['status']=='unresolved'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(engine,'320px reflow')
            assert not errors and not external,(engine,errors,external)
            browser.close()
            print(f'PASS: {engine} undo, exact evidence, invalidation, focus and local-only assertions')

if __name__=='__main__': main()
