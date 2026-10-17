"""Cross-engine HTTP smoke and browser zoom checks (not native AT validation)."""
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

@contextmanager
def serve():
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(Path(__file__).resolve().parent)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try: yield f'http://127.0.0.1:{server.server_port}/index.html'
    finally:
        server.shutdown(); server.server_close(); worker.join(timeout=5)
from playwright.sync_api import sync_playwright

def main():
    with serve() as url, sync_playwright() as p:
        for name in ("chromium", "firefox", "webkit"):
            browser = getattr(p, name).launch(headless=True)
            page = browser.new_page(viewport={"width": 320, "height": 700})
            errors, external = [], []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("request", lambda r: external.append(r.url) if not r.url.startswith(url.rsplit("/", 1)[0] + "/") else None)
            response = page.goto(url, wait_until="networkidle")
            assert response.status == 200, (name, "HTTP")
            assert page.locator("#sourceId").is_visible(), (name, "module")
            page.locator("#sourceId").fill("000123")
            page.locator("#date").fill("2026-10-17")
            page.locator("#claim").fill("Synthetic cross-browser record")
            page.get_by_role("button", name="Add record").click()
            assert page.locator("#records li").count() == 1, (name, "record")
            assert not errors, (name, errors)
            assert not external, (name, external)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (name, "320px reflow", page.evaluate("""() => ({scroll:document.documentElement.scrollWidth, width:innerWidth, root:document.documentElement.getBoundingClientRect().toJSON(), body:document.body.getBoundingClientRect().toJSON(), nodes:[...document.querySelectorAll("body *")].map(e=>({tag:e.tagName,id:e.id,scroll:e.scrollWidth,client:e.clientWidth,offset:e.offsetWidth})).filter(x=>x.scroll>x.client+1).slice(0,12), offenders:[...document.querySelectorAll("body *")].filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,10).map(e=>({tag:e.tagName,id:e.id,right:Math.round(e.getBoundingClientRect().right)}))})"""))
            # CDP page-scale emulation is not equivalent to manual browser UI zoom.
            # Enlarged root text is a separate automated reflow proxy.
            if name == "chromium":
                cdp = page.context.new_cdp_session(page)
                cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 2})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (name, "2x page scale")
            page.evaluate("document.documentElement.style.fontSize = '32px'")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (name, "200% root text")
            browser.close()
            print(f"PASS: {name} HTTP/module/record/local-only/reflow/enlarged-text")
if __name__ == "__main__":
    main()
