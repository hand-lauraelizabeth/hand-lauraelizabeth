"""Chromium read-only regression: net price sort on static or live WordPress, mobile/desktop."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/"data/sprint3/college-search-national.v3.json").read_text())["institutions"]
STATIC="http://127.0.0.1:8766/college-search-sprint3.html"
LIVE="https://www.lauraelizabethhand.com/resources/data-decision-making-tools/college-career-explorer/"

def run(browser,url,width):
    page=browser.new_page(viewport={"width":width,"height":844},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.on("requestfailed",lambda e:errors.append("Failed "+e.url[:120]))
    response=page.goto(url,wait_until="domcontentloaded",timeout=35000)
    assert response is not None and response.status==200, (url,response.status if response else None)
    page.wait_for_function("""() => document.querySelector("#cs-result-count")?.textContent.includes("6,243 schools")""",timeout=35000)
    sort=page.locator("#cs-sort")
    assert sort.is_enabled()
    assert sort.locator("option").count()==4,sort.inner_text()
    assert page.locator("#cs-sort-note").is_visible()
    assert page.locator("#cs-net-unknown").inner_text()=="1,222"
    # Pure core is run in actual browser with its source-validated records, and returns
    # all 6243 entries, so check missing prices for both full order directions.
    overall=page.evaluate("""() => {
      const core=window.CollegeSearchCore;
      if(!core||typeof core.filterSchools!=="function")return null;
      return fetch(document.querySelector("#college-search").dataset.src).then(r=>r.json()).then(payload=>{
        const rows=core.validatePayload(payload),opts=core.resetFilterOptions();
        const lo=core.filterSchools(rows,{...opts,sort:"net-asc"});
        const hi=core.filterSchools(rows,{...opts,sort:"net-desc"});
        return {lo:lo.map(r=>[r.unitid,r.average_net_price]),hi:hi.map(r=>[r.unitid,r.average_net_price])};
      });
    }""")
    assert overall and len(overall["lo"])==len(overall["hi"])==6243
    for mode in ("lo","hi"):
        vals=[p for uid,p in overall[mode] if p is not None]
        assert len(vals)==5021
        assert all(p is None for uid,p in overall[mode][-1222:])
        assert vals==sorted(vals,reverse=(mode=="hi"))
    for option,expected in (("net-asc",overall["lo"]),("net-desc",overall["hi"])):
        sort.select_option(option)
        assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools")
        actual=page.locator(".cs-card > p.cs-visually-hidden").all_inner_texts()
        ids=[s.replace("Institution identifier ","") for s in actual]
        assert ids==[uid for uid,p in expected[:24]],(option,ids[:4],expected[:4])
        assert page.locator("#cs-active-sort").inner_text().lower().find("net price")>=0
    # Sorting must not change the result count or override the independent slider.
    page.locator("#cs-net-max").evaluate("""e=>{e.value="20000";e.dispatchEvent(new Event("input",{bubbles:true}));}""")
    assert page.locator("#cs-result-count").inner_text().startswith("3,083 schools")
    assert page.locator("#cs-sort").input_value()=="net-desc"
    page.locator("#cs-clear").click()
    assert sort.input_value()=="name-asc"
    assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools")
    assert page.locator("#cs-active-sort").inner_text()=="Sort: School name: A–Z"
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
    assert not errors,errors
    print("S3_NET_PRICE_SORT_BROWSER_PASS",json.dumps({"url":url,"width":width,
         "low":overall["lo"][0],"high":overall["hi"][0],"unknown_last":1222,
         "remaining_after_ceiling":3083,"errors":0},sort_keys=True),flush=True)
    page.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--live",action="store_true")
    args=p.parse_args()
    with sync_playwright() as api:
        browser=api.chromium.launch(headless=True)
        for width in (390,1440):run(browser,LIVE if args.live else STATIC,width)
        browser.close()
if __name__=="__main__":main()
