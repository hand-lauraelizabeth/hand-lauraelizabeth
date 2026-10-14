#!/usr/bin/env python3
"""Automated WCAG 2.0/2.1 A/AA audit for the responsible-AI tools.

Axe flags are software signals, not a substitute for keyboard and assistive-
technology review. Public-site tests use synthetic data only.
"""
from pathlib import Path
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[2]
AXE = (ROOT / "node_modules" / "axe-core" / "axe.min.js").read_text(encoding="utf-8")
BASE = "https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/"
WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

LIVE_TARGETS = [
 ("Live Prompt Lab", BASE + "prompt-lab/", "#prompt-lab", "prompt-lab"),
 ("Live Ethical AI Decision Lab", BASE + "ai-use-decision-lab/", "#ai-use-lab", "ai-use-lab"),
 ("Live Teaching Statistics with R", BASE + "teaching-statistics-with-r/", "#leh-r-teaching", "leh-r-teaching"),
 ("Live Teaching NLP with Python", BASE + "teaching-nlp-with-python/", "#leh-python-nlp", "leh-python-nlp"),
]
LOCAL_TARGETS = [
 ("Prompt Literacy Debugger", (ROOT / "projects/prompt-literacy-debugger/index.html").as_uri(), "main", None),
 ("Evidence-Safe Prompt Lab", (ROOT / "projects/evidence-safe-prompt-lab/index.html").as_uri(), "main", None),
 ("Ethical AI Scenario Auditor", (ROOT / "projects/ethical-ai-scenario-auditor/index.html").as_uri(), "main", None),
]

def run_axe(driver, selector):
    driver.execute_script(AXE)
    return driver.execute_async_script("""
      const done = arguments[arguments.length-1];
      const selector=arguments[0];
      const root=document.querySelector(selector);
      if(!root){done({error:'missing target '+selector});return;}
      window.axe.run(root,{runOnly:{type:'tag',values:arguments[1]}})
        .then(r=>done({violations:r.violations.map(v=>({
           id:v.id,impact:v.impact,description:v.help,
           nodes:v.nodes.map(n=>({selector:n.target,summary:n.failureSummary})).slice(0,8)
        }))}))
        .catch(e=>done({error:String(e)}));
    """,selector,WCAG)

def main():
    opts=Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1240,900")
    if os.environ.get("CHROME_BINARY"):
        opts.binary_location=os.environ["CHROME_BINARY"]
    svc=Service(executable_path=os.environ["CHROMEDRIVER_BINARY"]) if os.environ.get("CHROMEDRIVER_BINARY") else Service()
    driver=webdriver.Chrome(service=svc,options=opts)
    driver.set_script_timeout(60)
    all_failures=[]
    try:
        live = os.environ.get("RUN_LIVE_SITE_CHECKS", "").lower() in ("true","1","yes")
        targets = LOCAL_TARGETS + (LIVE_TARGETS if live else [])
        for name,url,selector,ready_id in targets:
            driver.get(url)
            if ready_id:
                WebDriverWait(driver,25).until(lambda d: d.execute_script(
                    "return document.getElementById(arguments[0])?.dataset.ready === '1'",ready_id))
            result=run_axe(driver,selector)
            if result.get("error"):
                all_failures.append((name,result["error"]))
                print("FAIL",name,result["error"],flush=True)
                continue
            violations=result["violations"]
            print(("PASS" if not violations else "FAIL"),name,
                  "automated WCAG 2.0/2.1 A/AA violations:",len(violations),flush=True)
            for v in violations:
                print("  "+v["id"]+" ("+str(v["impact"])+"): "+v["description"],flush=True)
                for n in v["nodes"]:
                    print("    "+str(n["selector"])+" -- "+str(n["summary"])[:350],flush=True)
            if violations:all_failures.append((name,violations))

            # Run a second pass after interactive content becomes visible.
            if ready_id == "ai-use-lab":
                driver.execute_script("document.getElementById('ai-task').value='A fictional campus-advising assistant';document.getElementById('ethical-audit-build').click()")
            elif ready_id == "prompt-lab":
                driver.execute_script("document.querySelector('#prompt-lab button[data-panel=ledger]').click();"
                   "document.getElementById('led-claim').value='Fictional finding';"
                   "document.getElementById('led-source').value='Fictional source 1';"
                   "document.getElementById('led-excerpt').value='Synthetic observation';"
                   "document.getElementById('led-add').click()")
            else:
                continue
            interactive=run_axe(driver,selector)
            if interactive.get("error") or interactive["violations"]:
                print("FAIL",name,"after interaction",interactive,flush=True)
                all_failures.append((name+" dynamic",interactive))
            else:
                print("PASS",name,"dynamic controls after interaction",flush=True)
        if live:
            # Verify the actual WordPress-embedded copies as delivered to visitors.
            driver.get("https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/")
            WebDriverWait(driver,25).until(lambda d: d.find_elements(By.ID,"responsible-ai-standalone-demos"))
            for anchor,name in [
                ("ethics-scenario-auditor","Ethical AI Scenario Auditor"),
                ("prompt-literacy-debugger-demo","Prompt Literacy Debugger"),
                ("evidence-safe-prompt-lab-demo","Evidence-Safe Prompt Lab"),
            ]:
                details=driver.find_element(By.ID,anchor)
                details.find_element(By.TAG_NAME,"summary").click()
                driver.switch_to.frame(details.find_element(By.TAG_NAME,"iframe"))
                WebDriverWait(driver,25).until(lambda d: name in d.find_element(By.TAG_NAME,"h1").text)
                report=run_axe(driver,"main")
                if report.get("error") or report.get("violations"):
                    print("FAIL published embedded",name,report,flush=True)
                    all_failures.append(("published embedded "+name,report))
                else:
                    print("PASS published embedded",name,"automated WCAG 2.0/2.1 A/AA violations: 0",flush=True)
                driver.switch_to.default_content()

        assert not all_failures, f"{len(all_failures)} accessibility regression group(s)"
    finally:
        driver.quit()

if __name__=="__main__":
    main()
