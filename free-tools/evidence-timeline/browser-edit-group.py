"""Synthetic HTTP-served acceptance for local related-record group editing."""
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

def add(page,source_id,claim,group=''):
    page.locator('#sourceId').fill(source_id)
    page.locator('#date').fill('2026-10-25')
    page.locator('#claim').fill(claim)
    page.locator('#group').fill(group)
    page.get_by_role('button',name='Add record').click()

def exported(page):
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
            add(page,'0001','Synthetic original',group='review')
            add(page,'cafe\u0301','Synthetic Unicode',group='review')
            add(page,'S-003','Synthetic formula-like ID')
            original=exported(page)
            assert len(original['records'])==3
            page.get_by_role('button',name='Edit group for 0001').click()
            field=page.locator('#group-edit-value')
            assert field.input_value()=='review'
            field.fill('UNSAVED')
            assert exported(page)==original,(engine,'unsaved group leaked to export')
            page.once('dialog',lambda dialog: dialog.dismiss())
            page.get_by_role('button',name='Edit group for cafe\u0301').click()
            assert page.locator('#group-edit-source').inner_text()=='Source ID: 0001'
            page.once('dialog',lambda dialog: dialog.accept())
            page.get_by_role('button',name='Edit group for cafe\u0301').click()
            assert field.input_value()=='review'
            field.fill('new\u00a0group')
            page.locator('#review-filter').select_option('disputed')
            assert field.input_value()=='new\u00a0group',(engine,'unrelated render lost draft')
            page.locator('#review-filter').select_option('all')
            page.locator('#group-edit-form').evaluate("(form) => form.requestSubmit()")
            saved=exported(page)
            assert next(r for r in saved['records'] if r['sourceId']=='cafe\u0301')['group']=='new\u00a0group'
            assert next(r for r in saved['records'] if r['sourceId']=='0001')['group']=='review'
            assert not page.locator('#group-edit-panel').is_visible()
            assert page.evaluate('document.activeElement.dataset.editGroup')=='cafe\u0301'
            page.get_by_role('button',name='Edit group for S-003').click()
            field.evaluate("(el) => el.value='x'.repeat(121)")
            page.get_by_role('button',name='Save group').click()
            assert page.locator('#group-edit-error').is_visible()
            assert page.evaluate('document.activeElement.id')=='group-edit-error'
            assert exported(page)==saved,(engine,'invalid group changed saved records')
            field.fill('=SUM(A1)')
            page.get_by_role('button',name='Save group').click()
            assert page.locator('#csv').is_disabled(),(engine,'formula-like group should block CSV')
            formula_snapshot=exported(page)
            assert next(r for r in formula_snapshot['records'] if r['sourceId']=='S-003')['group']=='=SUM(A1)'
            page.get_by_role('button',name='Edit group for S-003').click()
            field.fill('')
            page.get_by_role('button',name='Cancel group edit').click()
            assert exported(page)==formula_snapshot
            assert page.evaluate('document.activeElement.dataset.editGroup')=='S-003'
            page.get_by_role('button',name='Edit group for S-003').click()
            field.fill('')
            page.get_by_role('button',name='Save group').click()
            assert page.locator('#csv').is_enabled()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(engine,'320px reflow')
            assert not errors and not external,(engine,errors,external)
            browser.close()
            print(f'PASS: {engine} group edit, discard, invalid input, evidence export, focus, CSV gate and 320px')
if __name__=='__main__': main()
