#!/usr/bin/env python3
"""End-to-end checks for the two live interactive teaching lessons.

Synthetic inputs only. Tests all tabs, keyboard activation, chart/quiz
initialization and the absence of the obsolete R theme toggle.
"""
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

BASE="https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/"
LESSONS=[
 ("Teaching Statistics with R", BASE+"teaching-statistics-with-r/", "leh-r-teaching", ("why","clt","lm","df","quiz")),
 ("Teaching NLP with Python", BASE+"teaching-nlp-with-python/", "leh-python-nlp", ("why","pre","tf","nb","quiz")),
]

def run(d,name,url,id_,tabs):
    d.set_window_size(1280,900)
    d.get(url)
    wait=WebDriverWait(d,25)
    wait.until(lambda x: x.execute_script(
        "return document.getElementById(arguments[0])?.dataset.ready==='1'",id_))
    root=d.find_element(By.ID,id_)
    assert not root.find_elements(By.ID,"theme"),name+": obsolete theme button"
    for j,tab in enumerate(tabs):
        b=root.find_element(By.CSS_SELECTOR,f'#tabs button[data-t="{tab}"]')
        d.execute_script("arguments[0].scrollIntoView({block:'center'})",b)
        b.send_keys(Keys.ENTER)
        target=root.find_element(By.ID,tab)
        assert target.is_displayed(),name+": tab "+tab+" failed to show"
        assert b.get_attribute("aria-selected")=="true"
        assert b.get_attribute("aria-controls")==tab
        assert target.get_attribute("role")=="tabpanel"
        assert target.get_attribute("aria-labelledby")==b.get_attribute("id")
        assert sum(int(root.find_element(By.ID,x).is_displayed()) for x in tabs)==1
        print("PASS",name,"tab:",tab,flush=True)
    last=root.find_element(By.CSS_SELECTOR,'#tabs button[data-t="quiz"]')
    last.send_keys(Keys.HOME)
    assert d.execute_script("return document.activeElement.id")==("r-lesson-tab-why" if id_=="leh-r-teaching" else "nlp-lesson-tab-why")
    first=root.find_element(By.CSS_SELECTOR,'#tabs button[data-t="why"]')
    first.send_keys(Keys.ARROW_RIGHT)
    assert root.find_element(By.ID,tabs[1]).is_displayed(),name+": arrow navigation failed"
    root.find_element(By.CSS_SELECTOR,'#tabs button[data-t="quiz"]').send_keys(Keys.ENTER)
    answers=root.find_elements(By.CSS_SELECTOR,"#quiz .q .o")
    assert len(answers)>=8,name+": quiz answer buttons missing"
    answers[0].send_keys(Keys.ENTER)
    assert "Score:" in root.find_element(By.ID,"qsc").text
    d.set_window_size(390,800)
    assert d.execute_script("return document.documentElement.scrollWidth<=window.innerWidth+2"),name+" mobile overflow"
    errors=[i["message"] for i in d.get_log("browser") if i["level"]=="SEVERE" and "favicon.ico" not in i["message"]]
    assert not errors,name+" browser errors: "+str(errors)
    print("PASS",name,"all tabs, keyboard, semantics, quiz, mobile, no theme, console",flush=True)

def main():
    options=Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.set_capability("goog:loggingPrefs",{"browser":"ALL"})
    if os.environ.get("CHROME_BINARY"):
        options.binary_location=os.environ["CHROME_BINARY"]
    svc=Service(executable_path=os.environ["CHROMEDRIVER_BINARY"]) if os.environ.get("CHROMEDRIVER_BINARY") else Service()
    d=webdriver.Chrome(service=svc,options=options)
    try:
        for args in LESSONS:run(d,*args)
    finally:d.quit()

if __name__=="__main__":
    main()
