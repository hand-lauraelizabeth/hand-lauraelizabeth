#!/usr/bin/env python3
"""Read-only synthetic browser smoke tests for the two published WordPress AI resources.

These exercises do not submit to a server, publish, or enter real private data.
"""
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


BASE = "https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/"
PROMPT = BASE + "prompt-lab/"
ETHICS = BASE + "ai-use-decision-lab/"


def field(d, id_):
    return d.find_element(By.ID, id_)


def click(d, element):
    d.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", element)


def enter(d, id_, value):
    e = field(d, id_)
    e.clear()
    e.send_keys(value)


def ensure_no_js_errors(d, name):
    errors = [e["message"] for e in d.get_log("browser") if e["level"] == "SEVERE"
              and "favicon.ico" not in e["message"]]
    assert not errors, f"{name}: severe console errors: {errors}"


def assert_fit(d):
    d.set_window_size(390, 780)
    w, viewport = d.execute_script("return [document.documentElement.scrollWidth, window.innerWidth]")
    assert w <= viewport + 2, f"Mobile width overflow {w} > {viewport}"
    d.set_window_size(1280, 900)


def check_prompt_lab(d):
    d.get(PROMPT)
    wait = WebDriverWait(d, 20)
    wait.until(lambda x: x.find_elements(By.ID, "prompt-lab"))
    try:
        wait.until(lambda x: x.execute_script("return document.getElementById('prompt-lab')?.dataset.ready") == "1")
    except Exception:
        print("PROMPT DIAGNOSTICS", flush=True)
        print("URL", d.current_url, flush=True)
        print("Ready attrs", d.execute_script("return document.getElementById('prompt-lab')?.outerHTML.slice(0,230)"), flush=True)
        print("Script count", d.execute_script("return document.querySelectorAll('#prompt-lab script').length"), flush=True)
        print("Ledger tabs", len(d.find_elements(By.CSS_SELECTOR, '#prompt-lab [data-panel="ledger"]')), flush=True)
        print("Console", d.get_log("browser")[-20:], flush=True)
        raise
    assert field(d, "ledger").get_attribute("hidden") is not None
    click(d, d.find_element(By.CSS_SELECTOR, '#prompt-lab button[data-panel="ledger"]'))
    wait.until(lambda x: field(x, "ledger").is_displayed())

    click(d, field(d, "led-add"))
    assert "Enter a claim" in field(d, "led-status").text
    enter(d, "led-claim", "The synthetic pilot improved long-term placement outcomes.")
    enter(d, "led-source", "Fictional report A, table 3")
    enter(d, "led-excerpt", "The pilot counted appointments, not placement outcomes.")
    enter(d, "led-reason", "Outcome is not directly measured.")
    click(d, field(d, "led-add"))
    assert len(d.find_elements(By.CSS_SELECTOR, "#led-records .evidence-record")) == 1
    click(d, field(d, "led-generate"))
    built = field(d, "led-prompt").text
    assert "Fictional report A, table 3" in built
    assert "NO EVIDENCE" in built
    enter(d, "led-row-0-claim", "Revised synthetic claim")
    click(d, field(d, "led-copy"))
    assert "Rebuild" in field(d, "led-status").text or "Generate" in field(d, "led-status").text
    click(d, field(d, "led-transfer"))
    assert "REVIEWER-ASSIGNED EVIDENCE LEDGER" in field(d, "pr").get_attribute("value")
    assert field(d, "design").is_displayed()
    click(d, field(d, "build"))
    assert "TASK" not in field(d, "out").text[:4]  # empty task must not generate a completed prompt
    assert "Enter a task" in field(d, "out").text
    assert_fit(d)
    ensure_no_js_errors(d, "Prompt Lab")
    print("PASS LIVE Prompt Lab: script initialized, ledger, validation, stale state, transfer, missing task, mobile")


def check_ethics(d):
    d.get(ETHICS)
    wait = WebDriverWait(d, 20)
    wait.until(lambda x: x.find_elements(By.ID, "ai-use-lab"))
    wait.until(lambda x: x.execute_script("return document.getElementById('ai-use-lab')?.dataset.ready") == "1")
    assert len(d.find_elements(By.CSS_SELECTOR, "#ethical-audit-questions fieldset")) == 12
    click(d, field(d, "sample-high"))
    assert field(d, "tier").text == "STOP & CHECK"
    click(d, field(d, "ethical-audit-build"))
    assert len(d.find_elements(By.CSS_SELECTOR, "#ethical-audit-register .audit-risk")) == 12
    assert "12 not assessed" in field(d, "ethical-audit-summary").text
    enter(d, "ethical-risk-0-owner", "Fictional program owner")
    assert "Update review brief" in field(d, "ethical-audit-status").text
    click(d, field(d, "ethical-audit-refresh"))
    assert "Fictional program owner" in field(d, "ethical-audit-brief").text

    enter(d, "ai-task", "A different imaginary automated hiring workflow.")
    assert "out of date" in field(d, "ethical-audit-summary").text
    click(d, field(d, "ethical-audit-export"))
    assert "Build or rebuild" in field(d, "ethical-audit-status").text

    click(d, field(d, "record"))
    assert "Complete the task" in field(d, "record-out").text
    assert_fit(d)
    ensure_no_js_errors(d, "Ethical AI")
    print("PASS LIVE Ethical AI: script initialized, 12 domains, high-risk gate, edit/refresh, stale block, disclosure validation, mobile")


def main():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    if os.environ.get("CHROME_BINARY"):
        options.binary_location = os.environ["CHROME_BINARY"]
    svc = Service(executable_path=os.environ["CHROMEDRIVER_BINARY"]) if os.environ.get("CHROMEDRIVER_BINARY") else Service()
    driver = webdriver.Chrome(service=svc, options=options)
    try:
        check_prompt_lab(driver)
        check_ethics(driver)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
