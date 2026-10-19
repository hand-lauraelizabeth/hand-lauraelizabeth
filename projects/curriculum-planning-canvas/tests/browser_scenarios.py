#!/usr/bin/env python3
"""Browser checks for curriculum-planning navigation, guidance, and form state."""
from __future__ import annotations
import os
import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

DIR=Path(__file__).resolve().parents[1]

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def run_site(driver,url,label):
    driver.get(url)
    wait=WebDriverWait(driver,18)
    wait.until(lambda d:d.find_element(By.ID,"lc-tab-objectives").is_displayed())
    for tab,panel in [("lc-tab-objectives","lc-objectives"),("lc-tab-sequence","lc-sequence"),
                      ("lc-tab-review","lc-review"),("lc-tab-context","lc-context")]:
        driver.find_element(By.ID,tab).click()
        wait.until(lambda d:d.find_element(By.ID,panel).is_displayed())
        assert driver.find_element(By.ID,tab).get_attribute("href").endswith("#"+panel)
    guide=driver.find_element(By.CSS_SELECTOR,"#lc-context details.lc-guidance")
    guide.find_element(By.TAG_NAME,"summary").click()
    assert guide.get_attribute("open") is not None, label+" guide failed to expand"
    title=driver.find_element(By.ID,"lc-title")
    title.clear()
    title.send_keys("Independent curriculum browser test")
    driver.find_element(By.ID,"lc-tab-objectives").click()
    wait.until(lambda d:d.find_element(By.ID,"lc-objectives").is_displayed())
    assert len(driver.find_elements(By.CSS_SELECTOR,"#lc-objectives details.lc-guidance"))>=6
    driver.find_element(By.ID,"lc-tab-context").click()
    assert driver.find_element(By.ID,"lc-title").get_attribute("value")=="Independent curriculum browser test"
    driver.find_element(By.ID,"lc-demo").click()
    wait.until(lambda d:d.switch_to.alert)
    driver.switch_to.alert.accept()  # Replacing entered work must require confirmation.
    wait.until(lambda d:"Synthetic example" in d.find_element(By.ID,"lc-status").get_attribute("textContent"))
    driver.find_element(By.ID,"lc-tab-sequence").click()
    wait.until(lambda d:d.find_element(By.CSS_SELECTOR,"#lc-module-list .lc-module").is_displayed())
    assert len(driver.find_elements(By.CSS_SELECTOR,"#lc-module-list .lc-module"))==3
    driver.find_element(By.ID,"lc-tab-review").click()
    wait.until(lambda d:d.find_element(By.ID,"lc-review").is_displayed())
    assert driver.find_element(By.ID,"lc-brief").text.strip()
    driver.find_element(By.ID,"lc-tab-context").click()
    driver.find_element(By.ID,"lc-tab-context").send_keys(Keys.ARROW_RIGHT)
    wait.until(lambda d:d.find_element(By.ID,"lc-objectives").is_displayed())
    print("PASS",label,"tabs, keyboard, examples, persistence, sequence and review")

def main():
    port=None
    with socket.socket() as s:
        s.bind(("127.0.0.1",0));port=s.getsockname()[1]
    server=ThreadingHTTPServer(("127.0.0.1",port),partial(Quiet,directory=str(DIR)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    driver=None
    try:
        options=Options()
        for flag in ("--headless=new","--no-sandbox","--disable-dev-shm-usage","--window-size=1280,1200"):
            options.add_argument(flag)
        driver=webdriver.Chrome(options=options)
        local=f"http://127.0.0.1:{port}/index.html"
        run_site(driver,local,"versioned local canvas")
        # No-JavaScript anchor navigation is an independent safety net.
        driver.execute_cdp_cmd("Emulation.setScriptExecutionDisabled",{"value":True})
        driver.get(local)
        driver.find_element(By.ID,"lc-tab-objectives").click()
        WebDriverWait(driver,10).until(lambda d:d.find_element(By.ID,"lc-objectives").is_displayed())
        assert not driver.find_element(By.ID,"lc-context").is_displayed()
        driver.find_element(By.ID,"lc-tab-review").click()
        WebDriverWait(driver,10).until(lambda d:d.find_element(By.ID,"lc-review").is_displayed())
        print("PASS without JavaScript: objectives and review remain reachable")
        driver.execute_cdp_cmd("Emulation.setScriptExecutionDisabled",{"value":False})
        live=os.environ.get("LEH_LIVE_CANVAS_URL","").strip()
        if live:
            run_site(driver,live,"published WordPress canvas")
    finally:
        if driver: driver.quit()
        server.shutdown();server.server_close()
if __name__=="__main__": main()
