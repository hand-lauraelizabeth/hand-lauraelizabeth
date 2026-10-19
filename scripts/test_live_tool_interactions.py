#!/usr/bin/env python3
"""Synthetic-input browser checks for five live and versioned portfolio tools."""
import os,socket,threading,time
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

ROOT=Path(__file__).resolve().parents[1]
BASE="https://www.lauraelizabethhand.com/resources/"
TOOLS=[
("standards-check","projects/standards-check/index.html",BASE+"learning-curriculum-tools/standards-check/","cutoff"),
("prompt-literacy-debugger","projects/prompt-literacy-debugger/index.html",BASE+"learning-curriculum-tools/prompt-literacy-debugger/","example"),
("evidence-safe-prompt-lab","projects/evidence-safe-prompt-lab/index.html",BASE+"learning-curriculum-tools/evidence-safe-prompt-lab/","example"),
("ethical-ai-scenario-auditor","projects/ethical-ai-scenario-auditor/index.html",BASE+"learning-curriculum-tools/ethical-ai-scenario-auditor/","example"),
("audience-lifecycle-crm-migration","projects/audience-lifecycle-crm-migration/index.html",BASE+"project-operations-tools/audience-lifecycle-crm-migration-planner/","example")
]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def enter_app(driver,key):
    """Find controls in direct HTML or nested published WordPress frames."""
    deadline=time.monotonic()+18
    while time.monotonic()<deadline:
        driver.switch_to.default_content()
        if driver.find_elements(By.ID,key): return
        for frame in driver.find_elements(By.CSS_SELECTOR,"iframe"):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                if driver.find_elements(By.ID,key): return
                for nested in driver.find_elements(By.CSS_SELECTOR,"iframe"):
                    driver.switch_to.frame(nested)
                    if driver.find_elements(By.ID,key): return
                    driver.switch_to.parent_frame()
            except Exception: pass
        time.sleep(.25)
    raise AssertionError(f"Missing interactive #{key} on {driver.current_url}")

def text_contains(driver,id,required):
    WebDriverWait(driver,12).until(
        lambda d: required in d.find_element(By.ID,id).get_attribute("textContent"))

def check(driver,name,url,key,source):
    driver.get(url)
    enter_app(driver,key)
    wait=WebDriverWait(driver,12)
    if name=="standards-check":
        assert len(driver.find_elements(By.CSS_SELECTOR,"#scoreTable tr"))==9
        assert len(driver.find_elements(By.CSS_SELECTOR,"#groups .group"))==4
        cutoff=driver.find_element(By.ID,"cutoff")
        assert cutoff.get_attribute("value")=="3"
        cutoff.send_keys(Keys.ARROW_RIGHT)
        wait.until(lambda d:d.find_element(By.ID,"cutoffValue").text.strip()=="4")
        text_contains(driver,"groups","Std 1 reteach")
        driver.find_element(By.ID,"refresh").click()
        assert len(driver.find_elements(By.CSS_SELECTOR,"#scoreTable tr"))==9
    else:
        driver.find_element(By.ID,"example").click()
        expected={
            "prompt-literacy-debugger":("scaffold","ORIGINAL REQUEST"),
            "evidence-safe-prompt-lab":("prompt","EVIDENCE CONTRACT"),
            "ethical-ai-scenario-auditor":("prompt","REVIEW TASK"),
            "audience-lifecycle-crm-migration":("out","IMPLEMENTATION SEQUENCE")}
        output,phrase=expected[name]
        text_contains(driver,output,phrase)
        if name=="prompt-literacy-debugger":
            text_contains(driver,"result","explicit")
            driver.find_element(By.ID,"reset").click()
            wait.until(lambda d:d.find_element(By.ID,"prompt").get_attribute("value")=="")
        elif name=="evidence-safe-prompt-lab":
            driver.find_element(By.ID,"clear").click()
            wait.until(lambda d:d.find_element(By.ID,"goal").get_attribute("value")=="")
        elif name=="ethical-ai-scenario-auditor":
            text_contains(driver,"summary","attention index")
        else:
            assert driver.find_element(By.ID,"goal").get_attribute("value")
            assert driver.find_element(By.ID,"audience").get_attribute("value")
    print("PASS",source,name,"browser workflow",flush=True)

def main():
    with socket.socket() as s:
        s.bind(("127.0.0.1",0));port=s.getsockname()[1]
    server=ThreadingHTTPServer(("127.0.0.1",port),partial(Quiet,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    driver=None
    try:
        o=Options()
        for flag in ("--headless=new","--no-sandbox","--disable-dev-shm-usage","--window-size=1280,1100"):
            o.add_argument(flag)
        driver=webdriver.Chrome(options=o)
        for name,path,live,key in TOOLS:
            check(driver,name,f"http://127.0.0.1:{port}/{path}",key,"versioned")
            if os.environ.get("LEH_TEST_LIVE_TOOLS","1")=="1":
                check(driver,name,live,key,"published")
        print("PASS five tools: local and WordPress",flush=True)
    finally:
        if driver: driver.quit()
        server.shutdown();server.server_close()
if __name__=="__main__": main()
