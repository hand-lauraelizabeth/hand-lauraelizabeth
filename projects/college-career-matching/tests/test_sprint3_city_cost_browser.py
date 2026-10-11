"""Functional Chromium regression for City multi-select and price filters, both widths."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import re

ROOT=Path(__file__).resolve().parents[1]
URL="http://127.0.0.1:8766/college-search-sprint3.html"
DATA=json.loads((ROOT/"data/sprint3/college-search-national.v3.json").read_text())["institutions"]
assert len(DATA)==6243

def count(**params):
    values=list(DATA.values())
    for key,value in params.items():
        if key=="cities":
            values=[r for r in values if r["state"]+"|"+r["city"] in value]
        elif key=="net":
            values=[r for r in values if r["average_net_price"] is not None and r["average_net_price"]<=value]
        elif key=="cost":
            values=[r for r in values if r["annual_cost"] is not None and r["annual_cost"]<=value]
        else:values=[r for r in values if r[key]==value]
    return len(values)

def shown(page):
    return int(page.locator("#cs-result-count").inner_text().split(" ")[0].replace(",",""))

def run(browser,width):
    page=browser.new_page(viewport={"width":width,"height":844},device_scale_factor=1)
    failures=[]
    page.on("pageerror",lambda e:failures.append(str(e)))
    page.goto(URL,wait_until="domcontentloaded")
    page.wait_for_function("document.querySelector('#cs-result-count')?.textContent.includes('6,243 schools')",timeout=30000)
    assert shown(page)==6243
    assert page.locator(".cs-card").count()==24
    assert page.locator("#cs-net-unknown").inner_text()=="1,222"
    assert page.locator("#cs-cost-unknown").inner_text()=="1,221"
    assert page.locator("#cs-control-unknown").inner_text()=="0"
    assert page.locator("#cs-city-search").is_enabled()
    assert page.locator("#cs-net-max").is_enabled()
    assert page.locator("#cs-cost-max").is_enabled()
    for option,expected in [("public",2044),("private_nonprofit",1890),("private_for_profit",2309)]:
        page.locator("#cs-control").select_option(option)
        assert shown(page)==expected
    page.locator("#cs-clear").click()
    assert shown(page)==6243
    page.locator("#cs-city-details").evaluate("(e)=>{e.open=true}")
    search=page.locator("#cs-city-search")
    search.fill("Cambridge")
    target=page.locator("#cs-city-options button").filter(has_text="Cambridge, MA")
    assert target.count()>0
    target.first.click()
    assert shown(page)==count(cities={"MA|Cambridge"})
    search.fill("Boston")
    target=page.locator("#cs-city-options button").filter(has_text="Boston, MA")
    assert target.count()>0
    target.first.click()
    assert shown(page)==count(cities={"MA|Cambridge","MA|Boston"})
    assert page.locator("#cs-city-selected button").count()==2
    assert "2 selected" in page.locator("#cs-city-count").inner_text()
    page.locator("#cs-clear").click()
    assert shown(page)==6243
    assert page.locator("#cs-city-selected button").count()==0
    # Independent price maxima; null records excluded only when limit active.
    net=page.locator("#cs-net-max")
    net.evaluate("(e)=>{e.value='20000';e.dispatchEvent(new Event('input',{bubbles:true}));}")
    assert shown(page)==count(net=20000)
    assert page.locator("#cs-net-output").inner_text()=="$20,000"
    cost=page.locator("#cs-cost-max")
    cost.evaluate("(e)=>{e.value='40000';e.dispatchEvent(new Event('input',{bubbles:true}));}")
    assert shown(page)==count(net=20000,cost=40000)
    assert page.locator("#cs-cost-output").inner_text()=="$40,000"
    assert page.locator("#cs-active-list").inner_text().find("Max annual cost")>=0
    page.locator("#cs-clear").click()
    assert shown(page)==6243
    assert page.locator("#cs-net-output").inner_text()=="Any"
    assert page.locator("#cs-cost-output").inner_text()=="Any"
    assert "Annual cost (estimated)" in page.locator(".cs-card").all_inner_texts()[0] or any("Annual cost (estimated)" in t for t in page.locator(".cs-card").all_inner_texts())
    # Card displays tuition when source has data; cost filter ONLY uses annual cost.
    assert page.locator(".cs-card .cs-costs").count()>0
    assert any("Tuition and fees" in t for t in page.locator(".cs-card").all_inner_texts())
    assert page.locator("#cs-show-more").is_visible()
    page.locator("#cs-show-more").click()
    assert page.locator(".cs-card").count()==48
    assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")
    assert not failures,failures
    print("S3_COST_CITY_CHROMIUM_PASS",json.dumps({"width":width,"records":6243,
           "city_multi":["Cambridge, MA","Boston, MA"],"net_20000":count(net=20000),
           "net_20000_cost_40000":count(net=20000,cost=40000)},sort_keys=True))
    page.close()

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True)
        for width in (390,1440):run(b,width)
        b.close()
if __name__=="__main__":main()
