"""HTTP-served synthetic source-ID lookup and evidence-integrity acceptance."""
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
    finally: server.shutdown();server.server_close();thread.join(timeout=5)

def add(page,source_id,claim,status='reported'):
    page.locator('#sourceId').fill(source_id)
    page.locator('#date').fill('2026-10-25')
    page.locator('#claim').fill(claim)
    page.locator('#status').select_option(status)
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
            add(page,'000123','Synthetic café evidence')
            add(page,'ABC-000123','Synthetic other',status='disputed')
            add(page,'cafe\u0301','Synthetic decomposed')
            original=export(page)
            assert len(original['records'])==3
            find=page.get_by_role('searchbox',name='Find by source ID (literal, case-sensitive)')
            find.fill('000123')
            assert 'Showing 2 of 3' in page.locator('#count').inner_text()
            assert len(page.locator('#records > li').all())==2
            assert export(page)==original,(engine,'filtered export must preserve all evidence')
            find.fill('abc')
            assert 'Showing 0 of 3' in page.locator('#count').inner_text()
            assert 'No records match' in page.locator('#empty').inner_text()
            find.fill('ABC')
            assert len(page.locator('#records > li').all())==1
            page.locator('#review-filter').select_option('reported')
            assert 'Showing 0 of 3' in page.locator('#count').inner_text()
            page.locator('#review-filter').select_option('all')
            find.fill('café')
            assert len(page.locator('#records > li').all())==0,(engine,'must not Unicode-normalize')
            find.fill('cafe\u0301')
            assert len(page.locator('#records > li').all())==1
            page.get_by_role('button',name='Clear source search').focus()
            page.keyboard.press('Enter')
            assert find.input_value()=='' and page.evaluate('document.activeElement.id')=='source-find'
            find.fill('000123')
            add(page,'NEW-000789','Synthetic new record')
            assert find.input_value()=='' and '4 records' in page.locator('#count').inner_text()
            page.locator('#review-filter').select_option('disputed')
            find.fill('ABC')
            assert 'Showing 1 of 4' in page.locator('#count').inner_text()
            snapshot=export(page)
            page.on('dialog',lambda dialog: dialog.accept())
            page.locator('#resume-json').set_input_files({'name':'synthetic.json','mimeType':'application/json','buffer':json.dumps(snapshot,ensure_ascii=False).encode('utf-8')})
            assert find.input_value()=='' and page.locator('#review-filter').input_value()=='all'
            assert export(page)==snapshot,(engine,'import preserves exact source evidence')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(engine,'320px reflow')
            assert not errors and not external,(engine,errors,external)
            browser.close()
            print(f'PASS: {engine} literal lookup, filtering, keyboard clear, export/import parity, local-only and 320px')
if __name__=='__main__': main()
