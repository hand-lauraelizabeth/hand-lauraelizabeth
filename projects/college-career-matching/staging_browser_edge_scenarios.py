#!/usr/bin/env python3
"""Negative/edge browser scenarios for the synthetic College + Career explorer."""
from __future__ import annotations
import copy,json,shutil,socket,subprocess,sys,tempfile,threading,time
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select,WebDriverWait

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
from public_explorer_deployment import inject
from staging_browser_harness import build_harness

class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def free_port():
 with socket.socket() as s:s.bind(("127.0.0.1",0));return s.getsockname()[1]

def start_api(built,api_port,origin):
 cmd=[sys.executable,str(P/"service_host.py"),"--snapshot",str(built["snapshot"]),"--manifest",str(built["manifest"]),"--model-version","synthetic-http-model-1","--allowed-origins",origin,"--bind","127.0.0.1","--port",str(api_port),"--quiet"]
 proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 import urllib.request
 end=time.time()+10
 while time.time()<end:
  if proc.poll() is not None:raise RuntimeError("staging API exited before healthy")
  try:
   with urllib.request.urlopen(f"http://127.0.0.1:{api_port}/health",timeout=1) as r:
    if r.status==200:return proc
  except Exception:time.sleep(.1)
 proc.terminate();raise RuntimeError("staging API did not become healthy")

def stop(proc):
 if not proc:return
 proc.terminate()
 try:proc.wait(timeout=3)
 except subprocess.TimeoutExpired:proc.kill()

def text_has(driver,selector,needle,timeout=10):
 WebDriverWait(driver,timeout).until(lambda d:needle in d.find_element(By.CSS_SELECTOR,selector).text)

def js_click(driver,element):driver.execute_script("arguments[0].click();",element)

def chrome():
 opts=Options();opts.add_argument("--headless=new");opts.add_argument("--no-sandbox");opts.add_argument("--disable-dev-shm-usage");opts.add_argument("--window-size=1440,1400")
 return webdriver.Chrome(options=opts)

def run():
 api_port,ui_port=free_port(),free_port()
 while ui_port==api_port:ui_port=free_port()
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);shutil.copytree(P/"prototype",root/"prototype")
  output=root/"staging-browser.html";built=build_harness(output,api_port)
  origin=f"http://127.0.0.1:{ui_port}"
  httpd=ThreadingHTTPServer(("127.0.0.1",ui_port),partial(Quiet,directory=str(root)));threading.Thread(target=httpd.serve_forever,daemon=True).start()
  proc=None;driver=None
  try:
   proc=start_api(built,api_port,origin);driver=chrome();wait=WebDriverWait(driver,12)
   driver.get(origin+"/staging-browser.html")
   wait.until(lambda d:d.find_element(By.ID,"leh-ccx").get_attribute("data-service-status")=="ready")
   text_has(driver,"#ccx-count","4 service-returned programs")

   # Zero-results UX: governed NY + NJ-only CIP combination.
   Select(driver.find_element(By.ID,"ccx-state")).select_by_value("NY")
   Select(driver.find_element(By.ID,"ccx-cip")).select_by_value("11.0199")
   text_has(driver,"#ccx-count","0 service-returned programs")
   text_has(driver,"#ccx-results","No service results returned.")
   assert not driver.find_elements(By.CSS_SELECTOR,".ccx-compare-toggle input")
   response=driver.execute_script("return document.getElementById('leh-ccx').getLastServiceResponse();")
   assert response["result_count"]==0 and response["results"]==[]

   # Reset and verify unresolved evidence stays visible as unknown rather than false.
   js_click(driver,driver.find_element(By.ID,"ccx-reset"))
   text_has(driver,"#ccx-count","4 service-returned programs")
   Select(driver.find_element(By.ID,"ccx-housing")).select_by_value("available")
   text_has(driver,"#ccx-count","4 service-returned programs")
   text_has(driver,"#ccx-results","Eligible with one or more unresolved must-have evidence fields.")
   text_has(driver,"#ccx-results","1 unresolved must-have evidence field")
   response=driver.execute_script("return document.getElementById('leh-ccx').getLastServiceResponse();")
   assert all(x["eligibility"]["status"]=="eligible_with_unknown" for x in response["results"])

   # Reset and verify three-program comparison cap against a four-result universe.
   js_click(driver,driver.find_element(By.ID,"ccx-reset"));text_has(driver,"#ccx-count","4 service-returned programs")
   boxes=wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,".ccx-compare-toggle input"));assert len(boxes)==4
   for box in boxes[:3]:js_click(driver,box)
   text_has(driver,"#ccx-compare-note","no winner is calculated in the browser")
   assert len(driver.find_elements(By.CSS_SELECTOR,"#ccx-compare-table th"))==4  # Field + 3 programs
   js_click(driver,boxes[3])
   text_has(driver,"#ccx-compare-note","Compare up to three programs at a time.")
   assert not boxes[3].is_selected()
   assert sum(1 for b in boxes if b.is_selected())==3

   # Runtime service loss must clear stale results/comparison instead of leaving them visible.
   stop(proc);proc=None
   Select(driver.find_element(By.ID,"ccx-state")).select_by_value("NY")
   wait.until(lambda d:d.find_element(By.ID,"leh-ccx").get_attribute("data-service-status")=="request-error")
   text_has(driver,"#ccx-results","Service response unavailable.")
   text_has(driver,"#ccx-results","Previous results were cleared.")
   assert driver.find_element(By.ID,"ccx-count").text=="No service response"
   assert driver.find_element(By.ID,"ccx-compare-table").text==""
   assert driver.execute_script("return document.getElementById('leh-ccx').getLastServiceResponse();") is None
   assert not driver.find_element(By.ID,"ccx-state").get_attribute("disabled")

   # Mismatched pinned metadata must block initialization and disable the matcher.
   mismatch=copy.deepcopy(built["runtime"]);mismatch["expected_identity"]["data_version"]="stale-synthetic-data-version"
   source=(P/"public-explorer.html").read_text(encoding="utf-8")
   bad=inject(source,mismatch).replace("<head>","<head>\n<meta name=\"robots\" content=\"noindex,nofollow\">",1)
   (root/"mismatch.html").write_text(bad,encoding="utf-8")
   proc=start_api(built,api_port,origin)
   driver.get(origin+"/mismatch.html")
   wait.until(lambda d:d.find_element(By.ID,"leh-ccx").get_attribute("data-service-status")=="error")
   text_has(driver,"#ccx-service-state","staging version identity mismatch")
   text_has(driver,"#ccx-results","Matcher unavailable.")
   assert driver.find_element(By.ID,"ccx-state").get_attribute("disabled")
   assert driver.find_element(By.ID,"ccx-reset").get_attribute("disabled")
   assert driver.find_element(By.ID,"ccx-count").text=="Matcher unavailable"

   print("PASS matcher edge scenarios: zero results, unknown evidence, compare cap, service loss, mismatched metadata")
  finally:
   if driver:driver.quit()
   stop(proc);httpd.shutdown();httpd.server_close()

if __name__=="__main__":run()
