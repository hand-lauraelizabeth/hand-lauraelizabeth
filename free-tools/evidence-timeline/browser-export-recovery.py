"""HTTP/CSP synthetic three-browser regression for local export failure recovery."""
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

INSTRUMENT="""(() => {
  window.__downloadTestMode='ok';
  window.__created=0;window.__revoked=0;
  const make=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL);
  URL.createObjectURL=(blob)=>{
    if(window.__downloadTestMode==='url')throw Error('synthetic URL block');
    window.__created++;return make(blob);
  };
  URL.revokeObjectURL=(url)=>{window.__revoked++;return revoke(url);};
  const click=HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click=function(){
    if(this.hasAttribute('download') && window.__downloadTestMode==='click')throw Error('synthetic click block');
    return click.call(this);
  };
})();"""
def main():
    with serve() as url, sync_playwright() as pw:
        for engine in ('chromium','firefox','webkit'):
            browser=getattr(pw,engine).launch(headless=True)
            page=browser.new_page(accept_downloads=True,viewport={'width':320,'height':720})
            errors=[];external=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            origin=url.rsplit('/',1)[0]+'/'
            page.on('request',lambda request:external.append(request.url) if not request.url.startswith(origin) and not request.url.startswith('blob:') else None)
            page.add_init_script(INSTRUMENT)
            assert page.goto(url,wait_until='networkidle').status==200
            page.locator('#sourceId').fill('0001')
            page.locator('#date').fill('2026-10-25')
            page.locator('#claim').fill('Synthetic example')
            page.get_by_role('button',name='Add record').click()
            assert '1 record' in page.locator('#count').inner_text()
            for mode,button in [('url','#csv'),('click','#json')]:
                page.evaluate('(mode)=>window.__downloadTestMode=mode',mode)
                page.locator(button).click()
                assert page.locator('#export-error').is_visible(),(engine,mode,'error visible')
                assert page.locator('#export-error').evaluate('(el)=>document.activeElement===el'),(engine,mode,'error focused')
                assert 'records are unchanged' in page.locator('#export-error').inner_text()
                assert '1 record' in page.locator('#count').inner_text()
                assert page.locator('a[download]').count()==0,(engine,mode,'temporary anchor cleaned')
                if mode=='click':
                    assert page.evaluate('window.__created===window.__revoked'),(engine,'failed click URL revoked')
            page.evaluate("window.__downloadTestMode='ok'")
            with page.expect_download() as csv_download:
                page.locator('#csv').click()
            assert csv_download.value.suggested_filename.endswith('.csv')
            csv_bytes=Path(csv_download.value.path()).read_bytes()
            assert b'0001' in csv_bytes and b'Synthetic example' in csv_bytes,(engine,'exact CSV fields')
            assert not page.locator('#export-error').is_visible()
            assert 'download started' in page.locator('#export-status').inner_text()
            with page.expect_download() as json_download:
                page.locator('#json').click()
            assert json_download.value.suggested_filename.endswith('.json')
            json_text=Path(json_download.value.path()).read_text(encoding='utf-8')
            assert '"sourceId": "0001"' in json_text,(engine,'exact source ID')
            assert not errors,(engine,errors)
            assert not external,(engine,external)
            browser.close()
            print('PASS:',engine,'blocked URL/click, cleanup, focused errors, CSV/JSON retry, CSP and no external requests')
if __name__=='__main__':main()
