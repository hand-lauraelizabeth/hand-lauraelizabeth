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
  wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,"#evidenceRows tr"))>=3)
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

  # Shared profile: reviewed nodes transfer to the discovery workspace.
  click(driver,wait,"profileSave")
  saved=driver.execute_script("return JSON.parse(localStorage.getItem('role-evidence.shared-profile.v1'))")
  assert saved["format"]=="role-evidence-candidate-profile" and saved["version"]==1
  assert any(n["verification_status"]=="verified" for n in saved["evidence_nodes"])
  driver.get(f"http://127.0.0.1:{port}/career-discovery-tracker.html")
  click(driver,wait,"profileLoad")
  wait.until(lambda d:"source sections" in d.find_element(By.ID,"profileMsg").text)
  assert "Synthetic example" in driver.find_element(By.CSS_SELECTOR,'[data-src="resume"] textarea').get_attribute("value")
  assert len(driver.find_elements(By.CSS_SELECTOR,".card"))>=1
  first=driver.find_element(By.CSS_SELECTOR,".card")
  first_id=first.get_attribute("data-id")
  Select(first.find_element(By.CSS_SELECTOR,'[data-k="s"]')).select_by_value("Applied")
  first.find_element(By.CSS_SELECTOR,'[data-k="n"]').send_keys("Preserve this synthetic application note.")
  click(driver,wait,"profileSave")
  driver.refresh()
  wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,".card"))>=1)
  saved_tracker=driver.execute_script("return JSON.parse(localStorage.getItem('rt.track'))")
  assert saved_tracker[first_id]["s"]=="Applied" and "synthetic application" in saved_tracker[first_id]["n"]
  driver.get(f"http://127.0.0.1:{port}/index.html")
  click(driver,wait,"profileLoad")
  assert "Synthetic example" in driver.find_element(By.ID,"candidate").get_attribute("value")
  assert "verified" in driver.find_element(By.ID,"evidenceRows").text
  driver.get(f"http://127.0.0.1:{port}/career-discovery-tracker.html")
  click(driver,wait,"profileLoad")
  assert driver.execute_script("return JSON.parse(localStorage.getItem('rt.track'))")[first_id]["s"]=="Applied"
  print("PASS Shared candidate profile: verified evidence transfer, same-origin browser storage, round-trip, application state preservation")

  print("PASS Role Evidence Engine browser scenarios: requirement matrix, evidence nodes, chronology, hard conditions, human review, claim guardrail")
 finally:
  if driver:driver.quit()
  srv.shutdown();srv.server_close()

if __name__=="__main__":run()
