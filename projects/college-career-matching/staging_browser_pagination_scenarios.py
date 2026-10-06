#!/usr/bin/env python3
"""Browser pagination and cross-page comparison scenarios for the matcher."""
from __future__ import annotations
import socket,subprocess,sys,tempfile,threading,time,shutil
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select,WebDriverWait

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
from staging_browser_harness import build_harness

class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def free_port():
 with socket.socket() as s:s.bind(("127.0.0.1",0));return s.getsockname()[1]

def wait_http(port,proc,timeout=10):
 end=time.time()+timeout
 while time.time()<end:
  if proc.poll() is not None:raise RuntimeError("staging API exited before healthy")
  try:
   with urlopen(f"http://127.0.0.1:{port}/health",timeout=1) as r:
    if r.status==200:return
  except Exception:time.sleep(.08)
 raise RuntimeError("staging API did not become healthy")

def text_has(driver,selector,needle,timeout=12):
 WebDriverWait(driver,timeout).until(lambda d:needle in d.find_element(By.CSS_SELECTOR,selector).text)

def click(driver,element):driver.execute_script("arguments[0].click();",element)

def run():
 api_port,ui_port=free_port(),free_port()
 while ui_port==api_port:ui_port=free_port()
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);shutil.copytree(P/"prototype",root/"prototype")
  output=root/"staging-browser.html";built=build_harness(output,api_port,candidate_count=27)
  origin=f"http://127.0.0.1:{ui_port}"
  proc=subprocess.Popen([sys.executable,str(P/"service_host.py"),"--snapshot",str(built["snapshot"]),"--manifest",str(built["manifest"]),"--model-version","synthetic-http-model-1","--allowed-origins",origin,"--bind","127.0.0.1","--port",str(api_port),"--quiet"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  httpd=ThreadingHTTPServer(("127.0.0.1",ui_port),partial(Quiet,directory=str(root)));threading.Thread(target=httpd.serve_forever,daemon=True).start()
  driver=None
  try:
   wait_http(api_port,proc)
   opts=Options();opts.add_argument("--headless=new");opts.add_argument("--no-sandbox");opts.add_argument("--disable-dev-shm-usage");opts.add_argument("--window-size=1440,1400")
   driver=webdriver.Chrome(options=opts);wait=WebDriverWait(driver,15)
   driver.get(origin+"/staging-browser.html")
   wait.until(lambda d:d.find_element(By.ID,"leh-ccx").get_attribute("data-service-status")=="ready")
   text_has(driver,"#ccx-count","Showing 1–20 of 27 service-returned programs")
   text_has(driver,"#ccx-page-status","Page 1 of 2")
   assert not driver.find_element(By.ID,"ccx-next").get_attribute("disabled")
   assert driver.find_element(By.ID,"ccx-prev").get_attribute("disabled")

   # Use ten per page so the test exercises three pages and a partial final page.
   Select(driver.find_element(By.ID,"ccx-page-size")).select_by_value("10")
   text_has(driver,"#ccx-count","Showing 1–10 of 27 service-returned programs")
   text_has(driver,"#ccx-page-status","Page 1 of 3")
   state=driver.execute_script("return document.getElementById('leh-ccx').getPaginationState();")
   assert state["page"]==1 and state["page_size"]==10 and state["total_pages"]==3

   first_name=driver.find_elements(By.CSS_SELECTOR,".ccx-card h3")[0].text
   first_box=driver.find_elements(By.CSS_SELECTOR,".ccx-compare-toggle input")[0];click(driver,first_box)
   assert driver.execute_script("return document.getElementById('leh-ccx').getPaginationState().selected_count;")==1

   # Page 2 preserves page-1 comparison selection and lets a second page contribute.
   click(driver,driver.find_element(By.ID,"ccx-next"))
   text_has(driver,"#ccx-count","Showing 11–20 of 27 service-returned programs")
   text_has(driver,"#ccx-page-status","Page 2 of 3")
   second_name=driver.find_elements(By.CSS_SELECTOR,".ccx-card h3")[0].text
   assert second_name!=first_name
   second_box=driver.find_elements(By.CSS_SELECTOR,".ccx-compare-toggle input")[0];click(driver,second_box)
   text_has(driver,"#ccx-compare-note","no winner is calculated in the browser")
   table=driver.find_element(By.ID,"ccx-compare-table").text
   assert first_name in table and second_name in table
   assert driver.execute_script("return document.getElementById('leh-ccx').getPaginationState().selected_count;")==2

   # Final page shows the partial range and correct button states; comparison persists.
   click(driver,driver.find_element(By.ID,"ccx-next"))
   text_has(driver,"#ccx-count","Showing 21–27 of 27 service-returned programs")
   text_has(driver,"#ccx-page-status","Page 3 of 3")
   assert driver.find_element(By.ID,"ccx-next").get_attribute("disabled")
   assert not driver.find_element(By.ID,"ccx-prev").get_attribute("disabled")
   table=driver.find_element(By.ID,"ccx-compare-table").text
   assert first_name in table and second_name in table

   # A genuine matching-criteria change resets to page 1 and clears old comparisons.
   Select(driver.find_element(By.ID,"ccx-state")).select_by_value("NY")
   wait.until(lambda d:d.find_element(By.ID,"leh-ccx").get_attribute("data-request-status")=="ready")
   state=driver.execute_script("return document.getElementById('leh-ccx').getPaginationState();")
   assert state["page"]==1 and state["selected_count"]==0
   assert driver.find_element(By.ID,"ccx-compare-table").text==""
   request=driver.execute_script("return document.getElementById('leh-ccx').getGovernedRequest();")
   assert request["page"]==1 and request["page_size"]==10
   assert any(x.get("field")=="state" and x.get("value")=="NY" for x in request["constraints"])

   print("PASS matcher pagination: ranges, navigation, partial final page, cross-page comparison, criteria reset")
  finally:
   if driver:driver.quit()
   httpd.shutdown();httpd.server_close();proc.terminate()
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.kill()

if __name__=="__main__":run()
