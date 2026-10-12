"""Browser regression against the real 6,243-institution static College Search."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json

ROOT=Path(__file__).resolve().parents[1]
URL="http://127.0.0.1:8766/college-search-sprint3.html"
DATA=json.loads((ROOT/"data/sprint3/college-search-scores.v3.json").read_text())
assert DATA["verified_band_counts"]=={"sat_complete_bands":1051,"act_complete_bands":965}

def run(browser,width):
    page=browser.new_page(viewport={"width":width,"height":844},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.goto(URL,wait_until="domcontentloaded")
    page.wait_for_function("document.querySelector('#cs-result-count')?.textContent.includes('6,243 schools')",timeout=30000)
    panel=page.locator("#cs-testing-details")
    assert panel.count()==1
    assert not panel.evaluate("(e)=>e.open"),"SAT/ACT panel should start collapsed"
    assert "No testing settings applied" in page.locator("#cs-testing-active").inner_text()
    panel.locator("summary").click()
    assert panel.evaluate("(e)=>e.open")
    assert page.locator("#cs-sat-low").is_visible()
    assert page.locator("#cs-own-act").is_visible()
    assert page.locator("#cs-sat-low").is_enabled()
    assert page.locator("#cs-act-high").is_enabled()
    assert page.locator("#cs-sat-band-unknown").inner_text()=="5,192"
    assert page.locator("#cs-act-band-unknown").inner_text()=="5,278"
    assert "1051 SAT and 965 ACT institutions" in page.locator("#cs-scores-status").inner_text()

    # Filter a named school for stable category assertions; badge is a score
    # convention only and disappears on reset or when measures conflict.
    page.locator("#cs-name").fill("Alabama A & M University")
    assert page.locator("#cs-result-count").inner_text().startswith("1 school")
    assert "U.S. Department of Education" in page.locator(".cs-card").first.inner_text()
    entry=DATA["institutions"]["100654"]
    assert entry[2:5]==[810,930,1040] or all(isinstance(n,int) for n in entry[2:5]),entry
    own=page.locator("#cs-own-sat")
    own.fill("1500")
    assert page.locator(".cs-card .cs-admission-badge").inner_text()=="SAFETY*"
    assert "1 active testing setting" in page.locator("#cs-testing-active").inner_text()
    # Collapsing a panel never clears a personal score or its comparison result.
    panel.locator("summary").click()
    assert not panel.evaluate("(e)=>e.open")
    assert page.locator(".cs-card .cs-admission-badge").inner_text()=="SAFETY*"
    assert "1 active testing setting" in page.locator("#cs-testing-active").inner_text()
    panel.locator("summary").click()
    assert panel.evaluate("(e)=>e.open")
    own.fill("880")
    assert page.locator(".cs-card .cs-admission-badge").inner_text()=="TARGET*"
    own.fill("400")
    assert page.locator(".cs-card .cs-admission-badge").inner_text()=="REACH*"
    own.fill("")
    assert page.locator(".cs-card .cs-admission-badge").count()==0
    assert page.locator(".cs-card .cs-score-source a").count()==1
    assert "Fall 2024" in page.locator(".cs-card .cs-score-source").inner_text()

    # Historical fall-2023 example: never label its source as fall 2024.
    page.locator("#cs-clear").click()
    page.locator("#cs-name").fill("Baptist Health College Little Rock")
    assert page.locator("#cs-result-count").inner_text().startswith("1 school")
    assert "Historical" in page.locator(".cs-card .cs-card-scores").inner_text()
    assert "Fall 2023" in page.locator(".cs-card .cs-card-scores").inner_text()
    assert "reported median 18" in page.locator(".cs-card .cs-card-scores").inner_text()
    ownACT=page.locator("#cs-own-act")
    ownACT.fill("30")
    assert page.locator(".cs-card .cs-admission-badge").inner_text()=="SAFETY*"
    ownACT.fill("18")
    assert page.locator(".cs-card .cs-admission-badge").inner_text()=="TARGET*"
    ownACT.fill("2")
    assert page.locator(".cs-card .cs-admission-badge").inner_text()=="REACH*"
    assert "historical" in page.locator(".cs-card .cs-admission-badge").get_attribute("aria-label").lower()
    ownACT.fill("")
    assert page.locator(".cs-card .cs-admission-badge").count()==0

    # Range filtering counts and excludes schools with an unknown SAT average.
    page.locator("#cs-clear").click()
    assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools")
    page.locator("#cs-sat-low").evaluate("""e=>{
      e.value="1200";e.dispatchEvent(new Event("input",{bubbles:true}));
    }""")
    actual=int(page.locator("#cs-result-count").inner_text().split()[0].replace(",",""))
    expected=sum(1 for v in DATA["institutions"].values() if v[0] is not None and 1200<=v[0]<=1600)
    assert actual==expected,(actual,expected)
    page.locator("#cs-clear").click()
    assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools")
    assert not page.evaluate("document.documentElement.scrollWidth>window.innerWidth+2")
    assert not errors,errors
    print(f"SCORE_ADMISSIONS_BROWSER_PASS width={width} percentiles=1051+965; categories=3; source=verified")
    page.close()

if __name__=="__main__":
    with sync_playwright() as api:
        browser=api.chromium.launch(headless=True)
        for width in (390,1440):run(browser,width)
        browser.close()
