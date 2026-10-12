"""Read-only production QA for the published national CIP6/AWLEVEL search."""
from playwright.sync_api import sync_playwright
import json

URL="https://www.lauraelizabethhand.com/resources/data-decision-making-tools/college-career-explorer/"
SHA="3abb9f458c9d0d43c857c64292dc407f3bd1e911"

def run(browser,width):
    page=browser.new_page(viewport={"width":width,"height":850},device_scale_factor=1)
    errors=[];failed=[];assets=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.on("requestfailed",lambda r:failed.append(r.url))
    page.on("response",lambda r:assets.append((r.status,r.url)) if "college-career-matching/" in r.url else None)
    try:
        r=page.goto(URL,wait_until="domcontentloaded",timeout=40000)
        print("LIVE_INITIAL",width,r.status,page.title(),flush=True)
        if r.status==202 or "Just a moment" in page.title():
            page.wait_for_timeout(5000)
            r=page.reload(wait_until="domcontentloaded",timeout=40000)
            print("LIVE_RETRY",width,r.status,page.title(),flush=True)
        page.wait_for_function("document.querySelector('#cs-result-count')?.textContent.includes('6,243 schools')",timeout=60000)
        assert page.locator("#cs-program-details").count()==1
        assert page.locator("#cs-testing-details").count()==1
        assert not page.locator("#cs-program-details").evaluate("(e)=>e.open")
        assert not page.locator("#cs-testing-details").evaluate("(e)=>e.open")
        page.locator("#cs-testing-details summary").click()
        page.locator("#cs-name").fill("Alabama A & M University")
        assert page.locator("#cs-result-count").inner_text().startswith("1 school")
        page.locator("#cs-own-sat").fill("1500")
        assert page.locator(".cs-admission-badge").first.inner_text()=="SAFETY*"
        page.locator("#cs-clear").click()
        page.locator("#cs-testing-details summary").click()
        page.locator("#cs-program-details summary").click()
        page.wait_for_function("document.querySelector('#cs-program-status')?.textContent.includes('5,658 of 6,243')",timeout=90000)
        assert page.locator("#cs-program-query").get_attribute("placeholder").find("coding")>=0
        for plain,expected in [("nurse","51.3801"),("BSN","51.3801"),("LPN","51.3901"),
                               ("coding","11.0201"),("HR","52.1001"),("CIP 51.3801","51.3801")]:
            page.locator("#cs-program-query").fill(plain)
            first=page.locator("#cs-program-options button").first.inner_text()
            assert "CIP "+expected in first,(plain,first)
        page.locator("#cs-program-query").fill("UX design")
        assert "Related subject" in page.locator("#cs-program-options").inner_text()
        page.locator("#cs-program-query").fill("Registered Nursing")
        page.locator("#cs-program-options button").filter(has_text="CIP 51.3801").first.click()
        page.locator("#cs-award-level").select_option("5")
        result=int(page.locator("#cs-result-count").inner_text().split()[0].replace(",",""))
        assert result>0
        assert page.locator(".cs-card-program").count()>0
        assert "2024–25" in page.locator(".cs-card-program").first.inner_text()
        assert page.locator(".cs-card-program a").first.get_attribute("href").endswith("C2025_A.zip")
        page.locator("#cs-program-details summary").click()
        assert int(page.locator("#cs-result-count").inner_text().split()[0].replace(",",""))==result
        page.locator("#cs-clear").click()
        assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools")
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
        assert not errors,errors
        assert not failed,failed[:5]
        script_urls=[(status,url) for status,url in assets if url.endswith(".js")]
        assert len(script_urls)>=2 and all(status==200 and SHA in url for status,url in script_urls),script_urls
        print("LIVE_PROGRAM_SEARCH_PASS",json.dumps({"width":width,"nursing_bachelors":result,"network_requests":len(assets),"errors":len(errors)}),flush=True)
    except Exception as e:
        print("LIVE_PROGRAM_SEARCH_FAIL",json.dumps({"width":width,"error":repr(e),"title":page.title(),
            "program_status":page.locator("#cs-program-status").first.inner_text(timeout=1000) if page.locator("#cs-program-status").count() else "missing",
            "score_status":page.locator("#cs-scores-status").first.inner_text(timeout=1000) if page.locator("#cs-scores-status").count() else "missing",
            "request_failures":failed[:8],"script_statuses":[(s,u[:160]) for s,u in assets if u.endswith(".js")][:5],"page_errors":errors[:8]}),flush=True)
        raise
    finally:page.close()

if __name__=="__main__":
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for width in (390,1440):run(browser,width)
        browser.close()
