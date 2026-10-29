"""Synthetic HTTP-served three-engine regression for bounded related-group previews."""
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
def main():
    records=[]
    for i in range(20):
        group='<img src=x onerror=alert(1)>\u202e' if i//2==0 else ('L'*120 if i//2==1 else f'g{i//2}')
        records.append({'sourceId':('I'*120 if i==2 else f'{i:04d}'),'date':'2026-10-25',
                        'claim':f'Synthetic claim {i}','kind':'source','status':'reported','group':group})
    with serve() as url, sync_playwright() as pw:
        origin=url.rsplit('/',1)[0]+'/'
        for engine in ('chromium','firefox','webkit'):
            browser=getattr(pw,engine).launch(headless=True)
            page=browser.new_page(viewport={'width':320,'height':720},accept_downloads=True)
            errors=[];external=[]
            page.on('pageerror',lambda error: errors.append(str(error)))
            page.on('request',lambda request: external.append(request.url) if not request.url.startswith(origin) else None)
            page.on('dialog',lambda dialog:dialog.accept())
            assert page.goto(url,wait_until='networkidle').status==200
            page.locator('#resume-json').set_input_files({'name':'synthetic.json','mimeType':'application/json',
                'buffer':json.dumps({'schema':'evidence-timeline-v1','records':records}).encode('utf-8')})
            page.locator('#resume-json-status').get_by_text('20 records imported',exact=False).wait_for(timeout=30000)
            preview=page.locator('#groups').inner_text()
            assert '10 related-record groups' in preview,(engine,preview)
            assert 'Showing first 8 groups' in preview
            assert '2 additional groups not shown' in preview
            assert 'g7' in preview and 'g8' not in preview and 'g9' not in preview
            assert len(preview)<2500,(engine,len(preview))
            assert '72 additional characters not shown' in preview,(engine,'long group/ID truncated')
            assert 'I'*120 not in preview and 'L'*120 not in preview,(engine,'preview-only clipping')
            assert '\\u202e' in preview and '<img src=x onerror=alert(1)>' in preview
            assert page.locator('#groups img').count()==0
            page.locator('#group-find').fill('g9')
            assert page.locator('#records > li').count()==2
            with page.expect_download() as dl: page.locator('#json').click()
            evidence=json.loads(Path(dl.value.path()).read_text(encoding='utf-8'))
            assert evidence['records']==records,(engine,'full exact export')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(engine,'320px reflow')
            assert not errors and not external,(engine,errors,external)
            browser.close()
            print('PASS:',engine,'bounded group summary, exact 20-record JSON, hidden-group search, CSP, 320px')
if __name__=='__main__': main()
