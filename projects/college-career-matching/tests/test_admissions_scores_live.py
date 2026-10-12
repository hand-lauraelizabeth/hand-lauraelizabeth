"""Post-publish Chromium smoke: real WordPress, CDN assets, test categorization.
Run read-only with python tests/test_admissions_scores_live.py.
"""
from playwright.sync_api import sync_playwright
import json, os
URL="https://www.lauraelizabethhand.com/resources/data-decision-making-tools/college-career-explorer/"

def check(browser,width):
    errors=[]; failed=[]; sources=[]
    page=browser.new_page(viewport={"width":width,"height":844},device_scale_factor=1)
    page.on("pageerror", lambda e:errors.append(str(e)))
    page.on("requestfailed",lambda q:failed.append(q.url))
    page.on("response",lambda r:sources.append((r.status,r.url[:160])) if "college-search-scores" in r.url or "college-search-national.v3.json" in r.url or "college-search-sprint3-embed.js" in r.url else None)
    response=page.goto(URL,wait_until="domcontentloaded",timeout=40000)
    print("INITIAL",json.dumps({"width":width,"status":response.status,"title":page.title()}),flush=True)
    try:
        page.wait_for_function("""() => document.querySelector("#cs-result-count")?.textContent.includes("6,243 schools")""",timeout=48000)
        assert page.locator("#cs-sat-low").is_enabled(),"SAT filter not enabled"
        assert page.locator("#cs-act-high").is_enabled(),"ACT filter not enabled"
        assert page.locator("#cs-sat-band-unknown").inner_text()=="5,192"
        assert page.locator("#cs-act-band-unknown").inner_text()=="5,278"
        assert "1051 SAT and 965 ACT" in page.locator("#cs-scores-status").inner_text()
        page.locator("#cs-name").fill("Alabama A & M University")
        assert page.locator("#cs-result-count").inner_text().startswith("1 school")
        assert "Fall 2024" in page.locator(".cs-card .cs-score-source").first.inner_text()
        page.locator("#cs-own-sat").fill("1500")
        assert page.locator(".cs-card .cs-admission-badge").inner_text()=="SAFETY*"
        page.locator("#cs-clear").click()
        assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools")
        page.locator("#cs-name").fill("Baptist Health College Little Rock")
        assert "Fall 2023" in page.locator(".cs-card .cs-card-scores").inner_text()
        assert "Historical" in page.locator(".cs-card .cs-card-scores").inner_text()
        page.locator("#cs-own-act").fill("18")
        assert page.locator(".cs-card .cs-admission-badge").inner_text()=="TARGET*"
        page.locator("#cs-clear").click()
        assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools")
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
        assert not errors,errors
        print("PUBLIC_SCORE_SEARCH_PASS",json.dumps({"width":width,"network":sources,"failed_requests":failed[:3],"console_errors":errors}),flush=True)
    except Exception as err:
        print("PUBLIC_SCORE_SEARCH_FAIL",json.dumps({"width":width,"error":repr(err),"network":sources,"failed_requests":failed[:15],"console_errors":errors[:15],"result":page.locator("#cs-result-count").inner_text(),"load_status":page.locator("#cs-load-status").inner_text(),"score_status":page.locator("#cs-scores-status").inner_text(),"error_text":page.locator("#cs-error-text").inner_text()}),flush=True)
        raise
    finally:
        page.close()

if __name__=="__main__":
    with sync_playwright() as api:
        browser=api.chromium.launch(headless=True)
        for width in (390,1440):check(browser,width)
        browser.close()
