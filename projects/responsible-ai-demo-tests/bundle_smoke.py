#!/usr/bin/env python3
"""Check the built, unhosted responsible-AI preview with a local HTTP server."""
import os
from pathlib import Path
import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/"dist/responsible-ai"
TOOLS={
    "prompt-literacy-debugger":"Prompt Literacy Debugger",
    "evidence-safe-prompt-lab":"Evidence-Safe Prompt Lab",
    "ethical-ai-scenario-auditor":"Ethical AI Scenario Auditor",
}

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    assert (BUNDLE/"index.html").is_file(), "Build first"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    server=ThreadingHTTPServer(("127.0.0.1",port),partial(Quiet,directory=str(BUNDLE)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    opts=Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=390,780")
    opts.set_capability("goog:loggingPrefs",{"browser":"ALL"})
    if os.environ.get("CHROME_BINARY"):
        opts.binary_location=os.environ["CHROME_BINARY"]
    service=Service(executable_path=os.environ["CHROMEDRIVER_BINARY"]) if os.environ.get("CHROMEDRIVER_BINARY") else Service()
    d=webdriver.Chrome(service=service,options=opts)
    try:
        start=f"http://127.0.0.1:{port}/"
        d.get(start)
        assert d.find_element(By.TAG_NAME,"h1").text=="Responsible AI: interactive demonstrations"
        assert len(d.find_elements(By.CSS_SELECTOR,"main .card a[href]"))==3
        for slug,title in TOOLS.items():
            d.get(start)
            a=d.find_element(By.CSS_SELECTOR,f'main .card a[href="{slug}/index.html"]')
            a.click()
            assert d.current_url.endswith(f"/{slug}/index.html"),d.current_url
            assert d.find_element(By.TAG_NAME,"h1").text==title
            assert d.find_elements(By.TAG_NAME,"button")
            assert d.execute_script("return document.documentElement.scrollWidth<=window.innerWidth+2"),slug
            errors=[i["message"] for i in d.get_log("browser") if i["level"]=="SEVERE" and "favicon.ico" not in i["message"]]
            assert not errors, errors
            print("PASS preview navigation:",slug,"mobile, page loaded, no script errors")
    finally:
        d.quit()
        server.shutdown()
        server.server_close()

if __name__=="__main__":
    main()
