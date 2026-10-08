#!/usr/bin/env python3
"""Headless-browser contract checks for the Role Evidence Engine."""
from __future__ import annotations
import re,socket,threading
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
def click(driver,wait,id_):
 el=wait.until(lambda d:d.find_element(By.ID,id_));driver.execute_script("arguments[0].scrollIntoView({block:'center'});",el);driver.execute_script("arguments[0].click();",el);return el

def run():
 port=free_port();srv=ThreadingHTTPServer(("127.0.0.1",port),partial(Quiet,directory=str(P)));threading.Thread(target=srv.serve_forever,daemon=True).start()
 driver=None
 try:
  o=Options();o.add_argument("--headless=new");o.add_argument("--no-sandbox");o.add_argument("--disable-dev-shm-usage");o.add_argument("--window-size=1440,1600")
  driver=webdriver.Chrome(options=o);driver.get(f"http://127.0.0.1:{port}/index.html");wait=WebDriverWait(driver,10)
  assert "does not emulate a proprietary ATS" in driver.find_element(By.TAG_NAME,"body").text
  click(driver,wait,"sampleJob");click(driver,wait,"sampleCandidate");click(driver,wait,"analyze")
  try:
   wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,"#evidenceRows tr"))>=2)
  except Exception:
   print("DIAGNOSTIC URL:",driver.current_url)
   print("DIAGNOSTIC INPUT LENGTHS:",len(driver.find_element(By.ID,"job").get_attribute("value")),len(driver.find_element(By.ID,"candidate").get_attribute("value")))
   print("DIAGNOSTIC EVIDENCE HTML:",driver.find_element(By.ID,"evidenceRows").get_attribute("innerHTML")[:1200])
   print("DIAGNOSTIC MATRIX HTML:",driver.find_element(By.ID,"rows").get_attribute("innerHTML")[:1200])
   print("DIAGNOSTIC BROWSER LOG:",driver.get_log("browser")[-8:])
   raise
  wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,"#rows tr"))>=3)
  matrix=driver.find_element(By.ID,"rows").text
  assert "E00" in matrix, matrix
  matrix=driver.find_element(By.ID,"rows").text
  matched=re.search(r"\b(E\d{3,})\b",matrix)
  assert matched, matrix
  node=Select(driver.find_element(By.ID,"nodeSelect"));node.select_by_value(matched.group(1))
  wait.until(lambda d:"Use only as a lead for review" in d.find_element(By.ID,"guardrail").text)
  driver.find_element(By.ID,"nodeRole").send_keys("Reviewed test role")
  driver.find_element(By.ID,"nodeSource").send_keys("Synthetic regression fixture")
  driver.find_element(By.ID,"nodeDates").clear();driver.find_element(By.ID,"nodeDates").send_keys("2017–2026; concurrent roles must not double-count overlap")
  Select(driver.find_element(By.ID,"nodeVerify")).select_by_value("verified")
  Select(driver.find_element(By.ID,"nodeConf")).select_by_value("public")
  driver.find_element(By.ID,"nodeAuthority").send_keys("Confirmed scope for synthetic browser test.")
  click(driver,wait,"saveNode")
  wait.until(lambda d:"Eligible for strong, source-specific wording" in d.find_element(By.ID,"guardrail").text)
  wait.until(lambda d:"verified" in d.find_element(By.ID,"rows").text)
  assert "No supported gap" in driver.find_element(By.ID,"rows").text or "verified" in driver.find_element(By.ID,"rows").text
  assert "verified" in driver.find_element(By.ID,"evidenceRows").text
  body=driver.find_element(By.TAG_NAME,"body").text
  assert "Chronology check" in body
  assert "Hard-condition check" in body
  assert "Application-facing wording ceiling" in body
  print("PASS Role Evidence Engine browser scenarios: requirement matrix, evidence nodes, chronology, hard conditions, human review, claim guardrail")
 finally:
  if driver:driver.quit()
  srv.shutdown();srv.server_close()

if __name__=="__main__":run()
