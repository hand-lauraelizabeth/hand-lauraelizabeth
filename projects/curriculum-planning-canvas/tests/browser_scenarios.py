#!/usr/bin/env python3
"""Browser checks for curriculum-planning navigation, guidance, and form state."""
from __future__ import annotations
import os
import socket
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

DIR=Path(__file__).resolve().parents[1]

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def click_tab(driver, tab_id):
    """Click a real tab despite asynchronous WordPress sticky-header reflow.

    The header can change position *after* scrollIntoView's initial hit test
    and before Selenium dispatches the pointer click. Retry only genuine
    interception after scrolling into a stable region below the header.
    Never bypass hit testing with a JavaScript click.
    """
    for attempt in range(5):
        tab = driver.find_element(By.ID, tab_id)
        driver.execute_script(
            """const tab=arguments[0],rect=tab.getBoundingClientRect();
            document.documentElement.style.scrollBehavior='auto';
            const absoluteTop=window.scrollY+rect.top;
            const target=Math.max(0, absoluteTop-Math.max(140,innerHeight*0.3));
            window.scrollTo({top:target,behavior:'instant'});""", tab
        )
        time.sleep(0.2)
        try:
            WebDriverWait(driver, 2).until(
                lambda d: d.execute_script(
                    """const e=arguments[0],r=e.getBoundingClientRect();
                    const x=r.left+r.width/2,y=r.top+r.height/2;
                    const hit=document.elementFromPoint(x,y);
                    return r.width>0 && r.height>0 && y>=100 && y<innerHeight &&
                           (hit===e || e.contains(hit));""", tab
                )
            )
            tab.click()
            return
        except (ElementClickInterceptedException, TimeoutException) as exc:
            info = driver.execute_script(
                """const e=arguments[0],r=e.getBoundingClientRect();
                const x=r.left+r.width/2,y=r.top+r.height/2;
                const hit=document.elementFromPoint(x,y);
                return {attempt:arguments[1],tab:arguments[2],url:location.href,
                top:r.top,bottom:r.bottom,scrollY:window.scrollY,
                scrollHeight:document.documentElement.scrollHeight,
                viewportHeight:innerHeight,hitTag:hit?.tagName,
                hitId:hit?.id,hitText:(hit?.textContent||'').slice(0,65),
                headerTop:document.getElementById('et-top-navigation')?.getBoundingClientRect().top};""",
                tab, attempt + 1, tab_id
            )
            print("CANVAS POINTER DIAGNOSTIC", type(exc).__name__, info, flush=True)
            if attempt == 4:
                raise
            # The live header may animate into the hit target. Reposition.
            continue

def run_site(driver,url,label):
    driver.get(url)
    wait=WebDriverWait(driver,18)
    wait.until(lambda d:d.find_element(By.ID,"lc-tab-objectives").is_displayed())
    for tab,panel in [("lc-tab-objectives","lc-objectives"),("lc-tab-sequence","lc-sequence"),
                      ("lc-tab-review","lc-review"),("lc-tab-context","lc-context")]:
        click_tab(driver,tab)
        try:
            wait.until(lambda d:d.find_element(By.ID,panel).is_displayed())
        except Exception:
            diagnostics=driver.execute_script("""const r=document.getElementById('leh-canvas-app'),p=document.getElementById(arguments[0]),t=document.getElementById(arguments[1]);
return {url:location.href,ready:r?.dataset.ready,hash:location.hash,panelClass:p?.className,
panelDisplay:p?getComputedStyle(p).display:null,tabSelected:t?.getAttribute('aria-selected'),
scriptCount:document.querySelectorAll('#leh-canvas-app script').length,
cssFallback:[...document.querySelectorAll('#leh-canvas-app style')].some(s=>s.textContent.includes(':not([data-ready=')),
panelCount:document.querySelectorAll('#lc-objectives').length};""",panel,tab)
            print("CANVAS LIVE DIAGNOSTIC",label,tab,diagnostics,flush=True)
            try:
                served=driver.execute_async_script("""const done=arguments[arguments.length-1];
fetch(location.href,{cache:'no-store'}).then(r=>r.text()).then(t=>{
 const a=t.split('\\n');done({total:a.length,around:a.slice(475,485).map((line,i)=>((i+476)+': '+line).slice(0,700))});
}).catch(e=>done({error:String(e)}));""")
                print("SERVED PAGE SCRIPT LINES",served,flush=True)
            except Exception as ex: print("SOURCE INSPECTION ERROR",str(ex),flush=True)
            try: print("BROWSER CONSOLE",driver.get_log("browser")[-10:],flush=True)
            except Exception: pass
            raise
        assert driver.find_element(By.ID,tab).get_attribute("href").endswith("#"+panel)
    guide=driver.find_element(By.CSS_SELECTOR,"#lc-context details.lc-guidance")
    guide.find_element(By.TAG_NAME,"summary").click()
    assert guide.get_attribute("open") is not None, label+" guide failed to expand"
    title=driver.find_element(By.ID,"lc-title")
    title.clear()
    title.send_keys("Independent curriculum browser test")
    click_tab(driver,"lc-tab-objectives")
    wait.until(lambda d:d.find_element(By.ID,"lc-objectives").is_displayed())
    assert len(driver.find_elements(By.CSS_SELECTOR,"#lc-objectives details.lc-guidance"))>=6
    click_tab(driver,"lc-tab-context")
    assert driver.find_element(By.ID,"lc-title").get_attribute("value")=="Independent curriculum browser test"
    driver.find_element(By.ID,"lc-demo").click()
    wait.until(lambda d:d.switch_to.alert)
    driver.switch_to.alert.accept()  # Replacing entered work must require confirmation.
    wait.until(lambda d:"Synthetic example" in d.find_element(By.ID,"lc-status").get_attribute("textContent"))
    click_tab(driver,"lc-tab-sequence")
    wait.until(lambda d:d.find_element(By.CSS_SELECTOR,"#lc-module-list .lc-module").is_displayed())
    assert len(driver.find_elements(By.CSS_SELECTOR,"#lc-module-list .lc-module"))==3
    click_tab(driver,"lc-tab-review")
    wait.until(lambda d:d.find_element(By.ID,"lc-review").is_displayed())
    assert driver.find_element(By.ID,"lc-brief").text.strip()
    click_tab(driver,"lc-tab-context")
    driver.find_element(By.ID,"lc-tab-context").send_keys(Keys.ARROW_RIGHT)
    wait.until(lambda d:d.find_element(By.ID,"lc-objectives").is_displayed())
    print("PASS",label,"tabs, keyboard, examples, persistence, sequence and review")

def main():
    port=None
    with socket.socket() as s:
        s.bind(("127.0.0.1",0));port=s.getsockname()[1]
    server=ThreadingHTTPServer(("127.0.0.1",port),partial(Quiet,directory=str(DIR)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    driver=None
    try:
        options=Options()
        for flag in ("--headless=new","--no-sandbox","--disable-dev-shm-usage","--window-size=1280,1200"):
            options.add_argument(flag)
        driver=webdriver.Chrome(options=options)
        local=f"http://127.0.0.1:{port}/index.html"
        run_site(driver,local,"versioned local canvas")
        # No-JavaScript anchor navigation is an independent safety net.
        driver.execute_cdp_cmd("Emulation.setScriptExecutionDisabled",{"value":True})
        driver.get(local)
        click_tab(driver,"lc-tab-objectives")
        WebDriverWait(driver,10).until(lambda d:d.find_element(By.ID,"lc-objectives").is_displayed())
        assert not driver.find_element(By.ID,"lc-context").is_displayed()
        click_tab(driver,"lc-tab-review")
        WebDriverWait(driver,10).until(lambda d:d.find_element(By.ID,"lc-review").is_displayed())
        print("PASS without JavaScript: objectives and review remain reachable")
        driver.execute_cdp_cmd("Emulation.setScriptExecutionDisabled",{"value":False})
        live=os.environ.get("LEH_LIVE_CANVAS_URL","").strip()
        if live:
            run_site(driver,live,"published WordPress canvas")
    finally:
        if driver: driver.quit()
        server.shutdown();server.server_close()
if __name__=="__main__": main()
