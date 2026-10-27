"""Synthetic HTTP-served, three-browser group filtering and exact-export regression."""
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
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try: yield f'http://127.0.0.1:{server.server_port}/index.html'
    finally: server.shutdown();server.server_close();thread.join(timeout=5)
def add(page,source,group):
    page.locator('#sourceId').fill(source)
    page.locator('#date').fill('2026-10-25')
    page.locator('#claim').fill('Synthetic record '+source)
    page.locator('#group').fill(group)
    page.get_by_role('button',name='Add record').click()
def exported(page):
    with page.expect_download() as dl: page.get_by_role('button',name='Export exact JSON').click()
    return json.loads(dl.value.path().read_text(encoding='utf-8'))
def ids(page):
    return page.locator('#records > li h3').all_inner_texts()
def main():
    with serve() as url, sync_playwright() as pw:
        origin=url.rsplit('/',1)[0]+'/'
        for engine in ('chromium','firefox','webkit'):
            browser=getattr(pw,engine).launch(headless=True)
            page=browser.new_page(viewport={'width':320,'height':720},accept_downloads=True)
            errors=[];external=[]
            page.on('pageerror',lambda error: errors.append(str(error)))
            page.on('request',lambda request: external.append(request.url) if not request.url.startswith(origin) else None)
            assert page.goto(url,wait_until='networkidle').status==200
            add(page,'A-001','café')
            add(page,'A-002','cafe\u0301')
            add(page,'A-003','')
            add(page,'A-004','=SUM(A1)')
            original=exported(page)
            assert len(original['records'])==4
            search=page.locator('#group-find')
            search.fill('café')
            assert len(ids(page))==1 and ids(page)[0].startswith('A-001'),(engine,ids(page))
            assert 'Showing 1 of 4' in page.locator('#count').inner_text()
            search.fill('cafe\u0301')
            assert len(ids(page))==1 and ids(page)[0].startswith('A-002')
            search.fill('CAFÉ')
            assert ids(page)==[],(engine,'case folding')
            search.fill('cafe\u0301')
            page.locator('select[data-source-id="A-002"]').select_option('disputed')
            page.locator('#review-filter').select_option('disputed')
            assert len(ids(page))==1 and ids(page)[0].startswith('A-002')
            page.locator('#source-find').fill('A-003')
            assert ids(page)==[],(engine,'combined source/group/status filters')
            page.get_by_role('button',name='Clear source search').click()
            assert len(ids(page))==1
            page.locator('#review-filter').select_option('all')
            page.locator('#ungrouped-only').check()
            assert search.is_disabled() and search.input_value()==''
            assert len(ids(page))==1 and ids(page)[0].startswith('A-003')
            assert exported(page)['records'][0]['sourceId']==original['records'][0]['sourceId']
            page.get_by_role('button',name='Clear group filter').click()
            assert page.evaluate('document.activeElement.id')=='group-find'
            assert not search.is_disabled() and not page.locator('#ungrouped-only').is_checked()
            assert len(ids(page))==4
            search.fill('café')
            page.get_by_role('button',name='Edit group for A-001').click()
            page.locator('#group-edit-value').fill('updated')
            page.get_by_role('button',name='Save group').click()
            assert search.input_value()=='' and len(ids(page))==4
            assert page.evaluate('document.activeElement.dataset.editGroup')=='A-001'
            saved=exported(page)
            assert next(r for r in saved['records'] if r['sourceId']=='A-001')['group']=='updated'
            assert [(r['sourceId'],r['claim']) for r in saved['records']]==[(r['sourceId'],r['claim']) for r in original['records']]
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(engine,'320px reflow')
            assert not errors and not external,(engine,errors,external)
            browser.close()
            print('PASS:',engine,'group lookup, exact Unicode, status/source intersection, ungrouped, focus, JSON, 320px, local-only')
if __name__=='__main__': main()
