#!/usr/bin/env python3
"""Concurrency and transient-recovery browser scenarios for the staging matcher."""
from __future__ import annotations
import json,shutil,socket,subprocess,sys,tempfile,threading,time
from functools import partial
from http.server import BaseHTTPRequestHandler,SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen

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

def start_api(built,port):
 cmd=[sys.executable,str(P/"service_host.py"),"--snapshot",str(built["snapshot"]),"--manifest",str(built["manifest"]),"--model-version","synthetic-http-model-1","--bind","127.0.0.1","--port",str(port),"--quiet"]
 proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 end=time.time()+10
 while time.time()<end:
  if proc.poll() is not None:raise RuntimeError("staging API exited before healthy")
  try:
   with urlopen(f"http://127.0.0.1:{port}/health",timeout=1) as r:
    if r.status==200:return proc
  except Exception:time.sleep(.08)
 proc.terminate();raise RuntimeError("staging API did not become healthy")

def stop(proc):
 if not proc:return
 proc.terminate()
 try:proc.wait(timeout=3)
 except subprocess.TimeoutExpired:proc.kill()
 time.sleep(.15)

def state_value(body):
 try:
  request=json.loads(body.decode("utf-8"))
  for c in request.get("constraints",[]):
   if c.get("field")=="state":return c.get("value")
 except Exception:pass
 return None

class Proxy(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def cors(self,status=200,content_type="application/json; charset=utf-8"):
  self.send_response(status);self.send_header("Content-Type",content_type);self.send_header("Cache-Control","no-store")
  self.send_header("Access-Control-Allow-Origin",self.server.ui_origin);self.send_header("Vary","Origin")
  self.end_headers()
 def do_OPTIONS(self):
  self.send_response(204);self.send_header("Access-Control-Allow-Origin",self.server.ui_origin);self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS");self.send_header("Access-Control-Allow-Headers","Content-Type");self.end_headers()
 def relay(self,body=None):
  path=self.path;state=state_value(body or b"") if path=="/match" else None
  if path=="/match":
   with self.server.lock:self.server.seen.append(state)
   delay={"NJ":1.15,"NY":.65,"PA":.08}.get(state,0)
   if delay:time.sleep(delay)
  req=Request(f"http://127.0.0.1:{self.server.backend_port}{path}",data=body,method=self.command,headers={"Content-Type":"application/json"} if body is not None else {})
  try:
   with urlopen(req,timeout=4) as r:status=r.status;data=r.read();ctype=r.headers.get("Content-Type","application/json")
  except HTTPError as e:status=e.code;data=e.read();ctype=e.headers.get("Content-Type","application/json")
  except Exception as e:
   status=502;data=json.dumps({"schema_version":"1.0","error":{"code":"backend_unavailable","message":str(e)}}).encode();ctype="application/json"
  try:self.cors(status,ctype);self.wfile.write(data)
  except (BrokenPipeError,ConnectionResetError):pass
 def do_GET(self):self.relay()
 def do_POST(self):
  try:n=int(self.headers.get("Content-Length","0"))
  except ValueError:n=0
  self.relay(self.rfile.read(n))

def seen(proxy,state):
 with proxy.lock:return state in proxy.seen

def text_has(driver,selector,needle,timeout=10):
 WebDriverWait(driver,timeout).until(lambda d:needle in d.find_element(By.CSS_SELECTOR,selector).text)

def run():
 backend_port,proxy_port,ui_port=free_port(),free_port(),free_port()
 while len({backend_port,proxy_port,ui_port})<3:backend_port,proxy_port,ui_port=free_port(),free_port(),free_port()
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);shutil.copytree(P/"prototype",root/"prototype")
  # Build runtime against the latency proxy, not directly against the backend.
  built=build_harness(root/"staging-browser.html",proxy_port)
  origin=f"http://127.0.0.1:{ui_port}"
  ui=ThreadingHTTPServer(("127.0.0.1",ui_port),partial(Quiet,directory=str(root)));threading.Thread(target=ui.serve_forever,daemon=True).start()
  proxy=ThreadingHTTPServer(("127.0.0.1",proxy_port),Proxy);proxy.backend_port=backend_port;proxy.ui_origin=origin;proxy.seen=[];proxy.lock=threading.Lock();threading.Thread(target=proxy.serve_forever,daemon=True).start()
  api=None;driver=None
  try:
   api=start_api(built,backend_port)
   opts=Options();opts.add_argument("--headless=new");opts.add_argument("--no-sandbox");opts.add_argument("--disable-dev-shm-usage");opts.add_argument("--window-size=1440,1200")
   driver=webdriver.Chrome(options=opts);wait=WebDriverWait(driver,15)
   driver.get(origin+"/staging-browser.html")
   wait.until(lambda d:d.find_element(By.ID,"leh-ccx").get_attribute("data-service-status")=="ready")
   text_has(driver,"#ccx-count","4 service-returned programs")

   # Force three overlapping requests whose responses would naturally arrive PA -> NY -> NJ.
   state=Select(driver.find_element(By.ID,"ccx-state"))
   state.select_by_value("NJ");wait.until(lambda _d:seen(proxy,"NJ"))
   state.select_by_value("NY");wait.until(lambda _d:seen(proxy,"NY"))
   state.select_by_value("PA");wait.until(lambda _d:seen(proxy,"PA"))
   text_has(driver,"#ccx-count","1 service-returned program")
   text_has(driver,"#ccx-results","Cedar Valley College")
   time.sleep(1.35)  # allow superseded NJ/NY responses to finish at the proxy
   results=driver.find_element(By.ID,"ccx-results").text
   assert "Cedar Valley College" in results and "River State University" not in results and "North Harbor College" not in results
   req=json.loads(driver.find_element(By.ID,"leh-ccx").get_attribute("data-governed-request"))
   assert any(x.get("field")=="state" and x.get("value")=="PA" for x in req["constraints"])
   assert driver.find_element(By.ID,"leh-ccx").get_attribute("data-request-status")=="ready"
   assert driver.execute_script("return document.getElementById('leh-ccx').getRequestGeneration();")>=4

   # Take backend offline. A new request must clear stale PA results and expose Retry.
   stop(api);api=None
   state.select_by_value("NY")
   wait.until(lambda d:d.find_element(By.ID,"leh-ccx").get_attribute("data-service-status")=="request-error")
   text_has(driver,"#ccx-results","Previous results were cleared.")
   retry=driver.find_element(By.ID,"ccx-retry");assert retry.is_displayed() and retry.is_enabled()
   assert driver.execute_script("return document.getElementById('leh-ccx').getLastServiceResponse();") is None

   # Recover the same pinned service. Retry must revalidate metadata/options before matching.
   api=start_api(built,backend_port)
   driver.execute_script("arguments[0].click();",retry)
   wait.until(lambda d:d.find_element(By.ID,"leh-ccx").get_attribute("data-service-status")=="ready")
   wait.until(lambda d:d.find_element(By.ID,"leh-ccx").get_attribute("data-request-status")=="ready")
   text_has(driver,"#ccx-count","2 service-returned programs")
   results=driver.find_element(By.ID,"ccx-results").text
   assert "North Harbor College" in results and "Metro Public College" in results and "River State University" not in results
   assert not driver.find_element(By.ID,"ccx-retry").is_displayed()
   assert Select(driver.find_element(By.ID,"ccx-state")).first_selected_option.get_attribute("value")=="NY"

   print("PASS matcher concurrency/recovery: last-writer-wins under latency and governed retry after outage")
  finally:
   if driver:driver.quit()
   stop(api);proxy.shutdown();proxy.server_close();ui.shutdown();ui.server_close()

if __name__=="__main__":run()
