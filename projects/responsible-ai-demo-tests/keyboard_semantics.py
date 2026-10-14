#!/usr/bin/env python3
"""Keyboard and browser accessibility-tree regression tests for responsible AI.

Chromium keyboard events + Chrome's accessibility tree check interaction,
focus order and exposed labels. They do NOT emulate VoiceOver, NVDA or
TalkBack and cannot replace manual screen-reader testing. Uses synthetic data.
"""
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/"
SITE = [
    ("Prompt Lab", BASE + "prompt-lab/", "prompt-lab"),
    ("Ethical AI Decision Lab", BASE + "ai-use-decision-lab/", "ai-use-lab"),
]
LOCAL = [
    ("Prompt Literacy Debugger", ROOT / "projects/prompt-literacy-debugger/index.html", "assess", "result", "Please enter a prompt"),
    ("Evidence-Safe Prompt Lab", ROOT / "projects/evidence-safe-prompt-lab/index.html", "generate", "prompt", "Enter a goal"),
    ("Ethical AI Scenario Auditor", ROOT / "projects/ethical-ai-scenario-auditor/index.html", "assess", "summary", "Describe a scenario"),
]


def el(d, selector):
    return d.find_element(By.CSS_SELECTOR, selector)


def active_id(d):
    return d.execute_script("return document.activeElement.id")


def ax_matches(d, role, name):
    nodes = d.execute_cdp_cmd("Accessibility.getFullAXTree", {})["nodes"]
    return [n for n in nodes if n.get("role",{}).get("value") == role
            and n.get("name",{}).get("value") == name and not n.get("ignored")]


def check_prompt(d):
    d.get(SITE[0][1])
    WebDriverWait(d, 25).until(lambda x: x.execute_script(
        "return document.getElementById('prompt-lab')?.dataset.ready==='1'"))
    design = el(d, '#prompt-lab button[data-panel="design"]')
    design.send_keys(Keys.ARROW_RIGHT)
    assert active_id(d) == "prompt-tab-audit", f"Right arrow should activate Audit: {active_id(d)}"
    audit = el(d, '#prompt-lab button[data-panel="audit"]')
    assert audit.get_attribute("aria-selected") == "true"
    assert ax_matches(d, "tabpanel", "Audit a prompt"), "Audit panel needs an exposed accessible name"
    audit.send_keys(Keys.END)
    assert active_id(d) == "prompt-tab-teach"
    el(d, "#prompt-tab-teach").send_keys(Keys.HOME)
    assert active_id(d) == "prompt-tab-design"
    el(d, "#prompt-tab-design").send_keys(Keys.TAB)
    assert active_id(d) == "design", f"Tab should enter active panel: {active_id(d)}"
    panel = el(d, "#design")
    assert panel.is_displayed()
    assert el(d, "#out").get_attribute("tabindex") == "0"
    assert ax_matches(d, "region", "Generated prompt"), "Generated prompt region lacks accessible name"

    el(d, "#prompt-tab-design").send_keys(Keys.ARROW_RIGHT)
    el(d, "#prompt-tab-audit").send_keys(Keys.ARROW_RIGHT)
    assert active_id(d) == "prompt-tab-ledger"
    assert el(d, "#ledger").is_displayed()
    assert ax_matches(d, "tabpanel", "Evidence ledger"), "Ledger panel lacks accessible name"
    el(d, "#led-add").send_keys(Keys.ENTER)
    assert "Enter a claim" in el(d, "#led-status").text
    print("PASS live Prompt Lab: arrow/home/end tab navigation, focus order, named panels/output, keyboard validation")


def check_ethics(d):
    d.get(SITE[1][1])
    WebDriverWait(d, 25).until(lambda x: x.execute_script(
        "return document.getElementById('ai-use-lab')?.dataset.ready==='1'"))
    el(d, "#sample-high").send_keys(Keys.ENTER)
    assert el(d, "#tier").text == "STOP & CHECK"
    el(d, "#ethical-audit-build").send_keys(Keys.ENTER)
    assert len(d.find_elements(By.CSS_SELECTOR, "#ethical-audit-register .audit-risk")) == 12
    last = el(d, "#ethical-risk-11-state")
    last.send_keys(Keys.TAB)
    assert active_id(d) == "ethical-audit-brief", f"Tab must reach scrollable brief: {active_id(d)}"
    pre = el(d, "#ethical-audit-brief")
    assert pre.get_attribute("tabindex") == "0"
    assert d.execute_script("return getComputedStyle(arguments[0]).outlineStyle",pre) != "none", (
        "Focused review brief should have a visible outline")
    assert ax_matches(d, "generic", "Human review brief (scrollable)") or (
        ax_matches(d, "region", "Human review brief (scrollable)")), (
        "Review brief needs a named node in accessibility tree")
    pre.send_keys(Keys.ARROW_DOWN)
    print("PASS live Ethical AI Decision Lab: Enter activation, edit-form to brief tab order, focus indicator, named brief")


def check_standalone(d, name, file, control, output, expected):
    d.get(file.as_uri())
    # Keyboard activation without JavaScript clicks; testing on empty fields
    btn = el(d, "#" + control)
    btn.send_keys(Keys.ENTER)
    assert expected in el(d, "#" + output).text, (
        name + ": keyboard submission must show useful validation")
    pre = d.find_elements(By.CSS_SELECTOR, "main pre")
    for p in pre:
        assert p.get_attribute("tabindex") == "0", name + ": generated text must be keyboard focusable"
        assert p.get_attribute("aria-label"), name + ": generated text should be named"
        p.send_keys(Keys.TAB)
    assert ax_matches(d, "heading", name), name + ": named heading missing from accessibility tree"
    print("PASS standalone "+name+": keyboard activation, visible validation, focusable named output, heading semantics")


def main():
    opt=Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument("--window-size=1200,900")
    if os.environ.get("CHROME_BINARY"):
        opt.binary_location=os.environ["CHROME_BINARY"]
    svc=Service(executable_path=os.environ["CHROMEDRIVER_BINARY"]) if os.environ.get("CHROMEDRIVER_BINARY") else Service()
    d=webdriver.Chrome(service=svc,options=opt)
    try:
        if os.environ.get("RUN_LIVE_SITE_CHECKS","").lower() in ("true","1","yes"):
            check_prompt(d)
            check_ethics(d)
        for name,file,control,output,expected in LOCAL:
            check_standalone(d,name,file,control,output,expected)
    finally:
        d.quit()


if __name__=="__main__":
    main()
