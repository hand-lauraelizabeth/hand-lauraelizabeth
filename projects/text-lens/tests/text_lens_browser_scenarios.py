#!/usr/bin/env python3
"""Headless-browser interaction checks for Text Lens corpus organization."""
from __future__ import annotations
import json,socket,tempfile,threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select,WebDriverWait

P=Path(__file__).resolve().parents[1]

class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def free_port():
 with socket.socket() as s:s.bind(("127.0.0.1",0));return s.getsockname()[1]

def run():
 port=free_port();httpd=ThreadingHTTPServer(("127.0.0.1",port),partial(Quiet,directory=str(P)))
 thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
 driver=None
 try:
  opts=Options();opts.add_argument("--headless=new");opts.add_argument("--no-sandbox");opts.add_argument("--disable-dev-shm-usage");opts.add_argument("--window-size=1440,1200")
  driver=webdriver.Chrome(options=opts);driver.get(f"http://127.0.0.1:{port}/text-lens.html")
  wait=WebDriverWait(driver,10)
  with tempfile.TemporaryDirectory() as td:
   a=Path(td)/"alpha.txt";b=Path(td)/"beta.txt"
   a.write_text("alpha evidence alpha method corpus reference evidence method "*12,encoding="utf-8")
   b.write_text("beta archive beta document corpus comparison archive document "*12,encoding="utf-8")
   upload=driver.find_element(By.ID,"fileA")
   # Chrome accepts newline-separated absolute paths for a multiple file input.
   upload.send_keys(str(a.resolve())+"\n"+str(b.resolve()))
   try:
    wait.until(lambda d:"alpha.txt" in d.find_element(By.ID,"docManagerRows").text and "beta.txt" in d.find_element(By.ID,"docManagerRows").text)
   except Exception as e:
    status=driver.find_element(By.ID,"status").text
    meta=driver.find_element(By.ID,"fileMetaA").text
    manager=driver.find_element(By.ID,"docManagerRows").text
    logs=[]
    try:logs=driver.get_log("browser")
    except Exception:pass
    raise AssertionError(f"local file load did not render documents; status={status!r}; meta={meta!r}; manager={manager!r}; browser_logs={logs!r}") from e
   manager=driver.find_element(By.ID,"docManagerRows").text
   assert "Text A" in manager and "2 documents" in manager
   assert len(driver.find_elements(By.CSS_SELECTOR,"input[data-refcheck]"))==2

   driver.find_element(By.ID,"refAll").click()
   wait.until(lambda d:"Custom reference set: 2 of 2" in d.find_element(By.ID,"refSummary").text)
   assert Select(driver.find_element(By.ID,"keyRef")).first_selected_option.get_attribute("value")=="custom"
   wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,".keyness-table tbody tr"))==2)
   assert "Target document" in driver.find_element(By.CSS_SELECTOR,".keyness-table").text
   assert "custom set:" in driver.find_element(By.CSS_SELECTOR,".keyness-table").text

   # Focus role is visible and narrows the presented keyness row.
   focus=Select(driver.find_element(By.ID,"focusDoc"));focus.select_by_index(1)
   wait.until(lambda d:"Focus" in d.find_element(By.ID,"docManagerRows").text)
   wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,".keyness-table tbody tr"))==1)

   setup=driver.execute_script("return buildCorpusSetup();")
   assert setup["contains_source_text"] is False
   assert len(setup["documents"])==2
   assert set(setup["documents"][0]).issubset({"source","name","size","last_modified","order"})
   serialized=json.dumps(setup).lower()
   assert "alpha evidence" not in serialized and "beta archive" not in serialized

   driver.find_element(By.ID,"refClear").click()
   wait.until(lambda d:"Reference mode: remainder" in d.find_element(By.ID,"refSummary").text)
   assert Select(driver.find_element(By.ID,"keyRef")).first_selected_option.get_attribute("value")=="remainder"

   print("PASS Text Lens browser scenarios: grouped corpus, custom references, focus role, keyness table, source-free setup")
 finally:
  if driver:driver.quit()
  httpd.shutdown();httpd.server_close()

if __name__=="__main__":run()
