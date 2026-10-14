#!/usr/bin/env python3
"""Test embedded responsible-AI tools on the published Learning & Curriculum hub.

Synthetic inputs only. This performs no changes to the WordPress site.
"""
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

HUB="https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/"
SCENARIOS=[
    ("ethics-scenario-auditor","Ethical AI Scenario Auditor",12,"scenario","assess","summary","12 not assessed"),
    ("prompt-literacy-debugger-demo","Prompt Literacy Debugger",7,"prompt","assess","result","explicit"),
    ("evidence-safe-prompt-lab-demo","Evidence-Safe Prompt Lab",None,"goal","generate","prompt","fictional"),
]

def check(driver):
    driver.get(HUB)
    wait=WebDriverWait(driver,25)
    wait.until(lambda d: d.find_elements(By.ID,"responsible-ai-standalone-demos"))
    for id_,title,n,field,button,out,expect in SCENARIOS:
        details=driver.find_element(By.ID,id_)
        summary=details.find_element(By.TAG_NAME,"summary")
        summary.send_keys(Keys.ENTER)
        assert details.get_attribute("open") is not None,f"{id_}: summary did not open using keyboard"
        iframe=details.find_element(By.TAG_NAME,"iframe")
        assert title in iframe.get_attribute("title")
        assert iframe.get_attribute("srcdoc"),f"{id_}: srcdoc missing"
        driver.switch_to.frame(iframe)
        if n is not None:
            wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR,"#questions fieldset"))==n)
        else:
            wait.until(lambda d: d.find_elements(By.ID,"goal"))
        assert title in driver.find_element(By.TAG_NAME,"h1").text
        form=driver.find_element(By.ID,field)
        form.send_keys("A fictional, public-information-only student advising scenario.")
        driver.find_element(By.ID,button).send_keys(Keys.ENTER)
        assert expect.lower() in driver.find_element(By.ID,out).text.lower(), (
            id_+": expected meaningful output from the embedded tool")
        driver.switch_to.default_content()
        print("PASS published hub embed:",title,"keyboard disclosure, frame loaded, synthetic interactive output")

    driver.set_window_size(390,780)
    assert driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth+2"), (
        "Published tool hub has mobile horizontal overflow")
    errors=[e["message"] for e in driver.get_log("browser")
            if e["level"]=="SEVERE" and "favicon.ico" not in e["message"]]
    assert not errors,f"Browser console errors: {errors}"
    print("PASS published tool hub: mobile width and console")

def main():
    options=Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.set_capability("goog:loggingPrefs",{"browser":"ALL"})
    if os.environ.get("CHROME_BINARY"):
        options.binary_location=os.environ["CHROME_BINARY"]
    service=Service(executable_path=os.environ["CHROMEDRIVER_BINARY"]) if os.environ.get("CHROMEDRIVER_BINARY") else Service()
    d=webdriver.Chrome(service=service,options=options)
    try:check(d)
    finally:d.quit()

if __name__=="__main__":
    main()
