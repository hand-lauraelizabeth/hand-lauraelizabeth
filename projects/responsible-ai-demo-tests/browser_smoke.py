#!/usr/bin/env python3
"""Real Chromium smoke checks for three client-side responsible-AI demonstrations.

Run from a repository checkout:
  python -m pip install selenium
  python projects/responsible-ai-demo-tests/browser_smoke.py
The test server binds only to localhost; all text is synthetic.
"""
from __future__ import annotations

import os
import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

ROOT = Path(__file__).resolve().parents[2]


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def field(driver, id_):
    return driver.find_element(By.ID, id_)


def click(driver, id_):
    element = field(driver, id_)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    driver.execute_script("arguments[0].click();", element)


def type_in(driver, id_, value):
    element = field(driver, id_)
    element.clear()
    element.send_keys(value)


def assert_mobile_fit(driver):
    driver.set_window_size(390, 780)
    dimensions = driver.execute_script(
        "return [document.documentElement.scrollWidth, window.innerWidth]"
    )
    assert dimensions[0] <= dimensions[1] + 2, (
        f"Horizontal viewport overflow: {dimensions!r}"
    )
    driver.set_window_size(1300, 1000)


def browser_errors(driver, name):
    errors = [
        e["message"]
        for e in driver.get_log("browser")
        if e["level"] == "SEVERE" and "favicon.ico" not in e["message"]
    ]
    assert not errors, f"{name}: browser console errors: {errors}"


def run_debugger(driver, base):
    driver.get(base + "/projects/prompt-literacy-debugger/index.html")
    wait = WebDriverWait(driver, 10)
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#questions fieldset")) == 7)
    click(driver, "assess")
    assert "Please enter a prompt" in field(driver, "result").text

    type_in(driver, "prompt", "Summarize these source documents in a table and verify citations.")
    Select(field(driver, "stakes")).select_by_value("high")
    Select(field(driver, "data")).select_by_value("sensitive")
    click(driver, "clues")
    assert "No dimension has been confirmed explicit" in field(driver, "clueStatus").text
    result = field(driver, "result").text
    assert "High consequence" in result and "Sensitive/confidential" in result
    assert "REVIEW BEFORE USING" in field(driver, "scaffold").text
    assert "Evidence boundary" in field(driver, "scaffold").text

    driver.find_element(By.CSS_SELECTOR, 'input[name="task"][value="2"]').click()
    click(driver, "assess")
    assert "Assessment generated" in field(driver, "status").text
    type_in(driver, "prompt", "Compare two public sources in a table.")
    assert "Build the coverage map again" in field(driver, "status").text
    click(driver, "copy")
    assert "Build a scaffold before copying" in field(driver, "status").text
    assert_mobile_fit(driver)
    click(driver, "reset")
    assert not field(driver, "prompt").get_attribute("value")
    assert "Describe the task" in field(driver, "result").text
    browser_errors(driver, "debugger")
    print("PASS Prompt Literacy Debugger: missing input, provisional clues, risk gates, stale-output block, reset, mobile")


def run_lab(driver, base):
    driver.get(base + "/projects/evidence-safe-prompt-lab/index.html")
    click(driver, "generate")
    assert "Enter a goal" in field(driver, "prompt").text
    type_in(driver, "goal", "Does the pilot show better employment outcomes?")
    type_in(driver, "claim", "The pilot improved employment outcomes.")
    Select(field(driver, "classification")).select_by_value("PARTIAL")
    type_in(driver, "rationale", "The paper reports a limited pilot without a comparison group.")
    click(driver, "addRecord")
    assert "provide a source ID and evidence excerpt" in field(driver, "ledgerStatus").text

    type_in(driver, "sourceid", "Synthetic Study A, page 3")
    type_in(driver, "excerpt", "The pilot reported more completed appointments, not employment outcomes.")
    type_in(driver, "counter", "Longitudinal comparison would be needed.")
    click(driver, "addRecord")
    assert len(driver.find_elements(By.CSS_SELECTOR, ".ledger-entry")) == 1
    assert "PARTIAL" in field(driver, "ledger").text

    click(driver, "generate")
    built = field(driver, "prompt").text
    assert "Synthetic Study A, page 3" in built
    assert "PARTIAL" in built
    assert "Longitudinal comparison" in built

    type_in(driver, "goal", "Revised goal after output was generated")
    click(driver, "copy")
    assert "Generate a prompt before copying" in field(driver, "status").text
    click(driver, "generate")
    assert "Revised goal" in field(driver, "prompt").text
    click(driver, "clear")
    assert len(driver.find_elements(By.CSS_SELECTOR, ".ledger-entry")) == 0
    assert field(driver, "only").is_selected()
    assert not field(driver, "privacy").is_selected()
    assert_mobile_fit(driver)
    browser_errors(driver, "evidence lab")
    print("PASS Evidence-Safe Prompt Lab: source requirements, evidence record, prompt export content, dirty-state, clear, mobile")


def run_auditor(driver, base):
    driver.get(base + "/projects/ethical-ai-scenario-auditor/index.html")
    wait = WebDriverWait(driver, 10)
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#questions fieldset")) == 12)
    click(driver, "assess")
    assert "Describe a scenario" in field(driver, "summary").text

    type_in(driver, "scenario", "A fictional advising team uses AI to suggest follow-up resources.")
    Select(field(driver, "impact")).select_by_value("3")
    click(driver, "assess")
    assert "12 not assessed" in field(driver, "summary").text
    assert "High-consequence scenario" in field(driver, "summary").text
    assert len(driver.find_elements(By.CSS_SELECTOR, ".risk-card")) == 12
    assert "/100" not in field(driver, "summary").text

    type_in(driver, "owner-0", "Accountable program director")
    assert "Update the review prompt" in field(driver, "status").text
    click(driver, "copy")
    assert "Assess a scenario first" in field(driver, "status").text
    click(driver, "refresh")
    assert "Accountable program director" in field(driver, "prompt").text
    assert "Oversight / contestability" in field(driver, "prompt").text

    type_in(driver, "scenario", "A different fictional advising workflow.")
    click(driver, "export")
    assert "Re-assess the scenario" in field(driver, "status").text.lower().replace("re-assess", "Re-assess")
    click(driver, "assess")
    assert "A different fictional advising workflow" in field(driver, "prompt").text
    assert_mobile_fit(driver)
    click(driver, "clear")
    assert "Assess scenario" in field(driver, "summary").text
    browser_errors(driver, "scenario auditor")
    print("PASS Ethical AI Scenario Auditor: missing input, unresolved risks, controls, owner edit, stale-output, reset, mobile")


def main():
    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    driver = None
    try:
        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1300,1000")
        opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})
        if os.environ.get("CHROME_BINARY"):
            opts.binary_location = os.environ["CHROME_BINARY"]
        svc = Service(executable_path=os.environ["CHROMEDRIVER_BINARY"]) if os.environ.get("CHROMEDRIVER_BINARY") else Service()
        driver = webdriver.Chrome(service=svc, options=opts)
        base = f"http://127.0.0.1:{port}"
        run_debugger(driver, base)
        run_lab(driver, base)
        run_auditor(driver, base)
    finally:
        if driver:
            driver.quit()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
