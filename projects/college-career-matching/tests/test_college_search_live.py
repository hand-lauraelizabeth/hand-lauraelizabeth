"""Read-only browser smoke checks against the ACTUAL public WordPress/Divi page.

Run only AFTER an owner-approved release. Tests do not modify WordPress content.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright

URL = "https://www.lauraelizabethhand.com/resources/data-decision-making-tools/college-career-explorer/"
OUT = Path("college-search-live-smoke")
OUT.mkdir(exist_ok=True)

def check_page(browser, label, width, height):
    page = browser.new_page(viewport={"width":width,"height":height}, device_scale_factor=1)
    errors=[]
    failed=[]
    responses=[]
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append("console:"+m.text) if m.type=="error" else None)
    page.on("requestfailed", lambda req: failed.append({"url":req.url[:240],"failure":req.failure}))
    page.on("response", lambda res: responses.append({"status":res.status,"url":res.url[:250]})
            if "college-search-national.v1.json" in res.url else None)
    report={"url":URL,"viewport":width,"label":label,"passed":False}
    try:
        nav=page.goto(URL,wait_until="domcontentloaded",timeout=30000)
        report["http_status"]=nav.status if nav else None
        page.locator("#college-search").wait_for(state="attached",timeout=20000)
        page.wait_for_function("""() => {
          const p=document.getElementById('cs-result-count');
          return p && p.textContent.includes('6,243 schools found');
        }""",timeout=35000)
        report["count"]=page.locator("#cs-result-count").inner_text()
        report["initial_cards"]=page.locator(".cs-card").count()
        assert report["initial_cards"]==24,report
        assert page.locator("#cs-name").is_enabled()
        assert page.locator("#cs-state").is_enabled()
        assert page.locator("#cs-sort").is_enabled()
        assert page.locator("details#cs-about-data").count()==1
        page.locator("#cs-name").fill("Harvard University")
        page.wait_for_function("""() => document.querySelectorAll('.cs-card').length===1""",timeout=8000)
        report["harvard_result"]=page.locator(".cs-card").first.inner_text()[:210]
        assert "Cambridge" in report["harvard_result"]
        page.locator("#cs-state").select_option("NY")
        assert "0 schools found" in page.locator("#cs-result-count").inner_text()
        page.locator("#cs-clear").click()
        assert "6,243 schools found" in page.locator("#cs-result-count").inner_text()
        page.locator("#cs-show-more").click()
        assert page.locator(".cs-card").count()==48
        assert page.locator("#cs-about-data").is_visible()
        report["show_more_cards"]=48
        report["horizontal_overflow"]=page.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
        report["passed"]=not report["horizontal_overflow"]
        print("LIVE_SEARCH_PASS",json.dumps(report,sort_keys=True),flush=True)
    except Exception as e:
        report["exception"]=repr(e)
        report["page_title"]=page.title()
        report["load_text"]=page.locator("#cs-load-status").inner_text() if page.locator("#cs-load-status").count() else None
        report["error_text"]=page.locator("#cs-error-text").inner_text() if page.locator("#cs-error-text").count() else None
        report["count_text"]=page.locator("#cs-result-count").inner_text() if page.locator("#cs-result-count").count() else None
        report["has_component_script"]=page.evaluate("!!document.querySelector('script[data-college-search]')")
        report["core_ready"]=page.evaluate("!!window.CollegeSearchCore")
        print("LIVE_SEARCH_FAIL",json.dumps(report,sort_keys=True),flush=True)
    finally:
        report["dataset_responses"]=responses
        report["page_errors"]=errors[:20]
        report["request_failures"]=failed[:20]
        page.screenshot(path=str(OUT/f"{label}.png"),full_page=False)
        (OUT/f"{label}.json").write_text(json.dumps(report,indent=2)+"\n")
        page.close()
    return report

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        results=[check_page(browser,"mobile",390,844),check_page(browser,"desktop",1440,900)]
        browser.close()
    print("LIVE_RESULTS",json.dumps(results,sort_keys=True))
    assert all(r["passed"] for r in results), "Live WordPress functional smoke failed"

if __name__=="__main__":
    main()
