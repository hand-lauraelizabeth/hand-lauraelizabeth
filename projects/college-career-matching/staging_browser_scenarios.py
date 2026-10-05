#!/usr/bin/env python3
"""Headless-browser interaction scenarios for the synthetic staging explorer.

Uses the real browser UI, ES-module client, and loopback HTTP service. All data
are fictional and the runtime remains explicitly non-production.
"""
from __future__ import annotations
import socket,subprocess,sys,tempfile,threading,time
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select,WebDriverWait

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
from staging_browser_harness import build_harness

class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def free_port():
 with socket.socket() as s:
  s.bind(("127.0.0.1",0));return s.getsockname()[1]

def wait_http(port,proc,timeout=10):
 import urllib.request
 end=time.time()+timeout
 while time.time()<end:
  if proc.poll() is not None:raise RuntimeError("staging API exited before becoming healthy")
  try:
   with urllib.request.urlopen(f"http://127.0.0.1:{port}/health",timeout=1) as r:
    if r.status==200:return
  except Exception:time.sleep(.1)
 raise RuntimeError("staging API did not become healthy")

def text_has(driver,selector,needle,timeout=10):
 WebDriverWait(driver,timeout).until(lambda d:needle in d.find_element(By.CSS_SELECTOR,selector).text)

def run():
 api_port,ui_port=free_port(),free_port()
 while ui_port==api_port:ui_port=free_port()
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)
  # Keep the explorer beside a copied prototype directory so its real ES module loads.
  import shutil
  shutil.copytree(P/"prototype",root/"prototype")
  output=root/"staging-browser.html"
  built=build_harness(output,api_port)
  origin=f"http://127.0.0.1:{ui_port}"
  cmd=[sys.executable,str(P/"service_host.py"),"--snapshot",str(built["snapshot"]),"--manifest",str(built["manifest"]),"--model-version","synthetic-http-model-1","--allowed-origins",origin,"--bind","127.0.0.1","--port",str(api_port),"--quiet"]
  proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  httpd=ThreadingHTTPServer(("127.0.0.1",ui_port),partial(Quiet,directory=str(root)))
  thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
  driver=None
  try:
   wait_http(api_port,proc)
   opts=Options();opts.add_argument("--headless=new");opts.add_argument("--no-sandbox");opts.add_argument("--disable-dev-shm-usage");opts.add_argument("--window-size=1440,1200")
   driver=webdriver.Chrome(options=opts)
   driver.get(origin+"/staging-browser.html")
   wait=WebDriverWait(driver,12)
   wait.until(lambda d:d.find_element(By.ID,"leh-ccx").get_attribute("data-ready")=="1")
   text_has(driver,"#ccx-service-state","Synthetic staging HTTP service")
   text_has(driver,"#ccx-service-state","production authorized: no")
   text_has(driver,"#ccx-mode-note","Synthetic staging mode:")
   text_has(driver,"#ccx-count","4 service-returned programs")
   assert "North Harbor College" in driver.find_element(By.ID,"ccx-results").text
   assert "Metro Public College" in driver.find_element(By.ID,"ccx-results").text
   assert "River State University" in driver.find_element(By.ID,"ccx-results").text
   assert "Cedar Valley College" in driver.find_element(By.ID,"ccx-results").text

   # Governed hard constraint: NJ should return only the fictional NJ candidate.
   Select(driver.find_element(By.ID,"ccx-state")).select_by_value("NJ")
   text_has(driver,"#ccx-request-state","1 must-have constraint")
   text_has(driver,"#ccx-count","1 service-returned program")
   results=driver.find_element(By.ID,"ccx-results").text
   assert "River State University" in results and "North Harbor College" not in results and "Metro Public College" not in results

   # NY + online narrows to North Harbor; verifies another real UI->HTTP request.
   Select(driver.find_element(By.ID,"ccx-state")).select_by_value("NY")
   online=driver.find_element(By.ID,"ccx-online")
   if not online.is_selected():online.click()
   text_has(driver,"#ccx-request-state","2 must-have constraints")
   text_has(driver,"#ccx-count","1 service-returned program")
   results=driver.find_element(By.ID,"ccx-results").text
   assert "North Harbor College" in results and "Metro Public College" not in results

   # Reset restores the full service-returned set and clears governed constraints.
   driver.find_element(By.ID,"ccx-reset").click()
   text_has(driver,"#ccx-request-state","0 must-have constraints")
   text_has(driver,"#ccx-count","4 service-returned programs")
   assert Select(driver.find_element(By.ID,"ccx-state")).first_selected_option.get_attribute("value")==""
   assert not driver.find_element(By.ID,"ccx-online").is_selected()

   # Compare two displayed programs; browser must present service fields without winner logic.
   boxes=wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,".ccx-compare-toggle input"))
   names=[x.text for x in driver.find_elements(By.CSS_SELECTOR,".ccx-card h3")]
   assert len(boxes)>=2 and len(names)==len(boxes)
   boxes[0].click();boxes[1].click()
   text_has(driver,"#ccx-compare-note","no winner is calculated in the browser")
   table=driver.find_element(By.ID,"ccx-compare-table").text
   assert names[0] in table and names[1] in table
   assert "Institution" in table and "Recommendation" in table

   # Clear comparison leaves results intact.
   driver.find_element(By.ID,"ccx-clear").click()
   text_has(driver,"#ccx-compare-note","Select two or three programs")
   assert driver.find_element(By.ID,"ccx-count").text.startswith("4 service-returned programs")

   print("PASS staging browser scenarios: state, online, request feedback, compare, reset, service-state language")
  finally:
   if driver:
    driver.quit()
   httpd.shutdown();httpd.server_close();proc.terminate()
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.kill()

if __name__=="__main__":run()
