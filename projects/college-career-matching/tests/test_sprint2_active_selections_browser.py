"""S2-05: browser checks for active selections, live result counts, and Clear."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
ROWS=list(json.loads((ROOT/"data/sprint2/college-search-national.v2.json").read_text())["institutions"].values())
URL="http://127.0.0.1:8766/college-search-sprint2.html"
FIELDS=("name","state","sort","control","locale","size")

def result_count(page):
    text=page.locator("#cs-result-count").inner_text()
    match=re.match(r"^([\d,]+) schools? found",text)
    assert match,text
    return int(match.group(1).replace(",",""))

def defaults(page):
    for field in FIELDS:
        assert page.locator("#cs-"+field).input_value()==("name-asc" if field=="sort" else ""),field
    assert result_count(page)==6243
    assert page.locator("#cs-active-none").is_visible()
    assert page.locator("#cs-active-none").inner_text()=="No filters applied."
    assert page.locator("#cs-active-list").is_hidden()
    assert page.locator("#cs-active-list li").count()==0
    assert page.locator("#cs-active-sort").inner_text()=="Sort: School name: A–Z"
    assert page.locator(".cs-card").count()==24
    assert "showing 24" in page.locator("#cs-result-count").inner_text()
    assert page.locator("#cs-show-more").is_visible()
    assert page.locator("#cs-clear").is_disabled()

def clear(page):
    assert page.locator("#cs-clear").is_enabled()
    page.locator("#cs-clear").click()
    defaults(page)

def active(page,labels,sort="Sort: School name: A–Z"):
    assert page.locator("#cs-active-list li").all_inner_texts()==labels
    assert page.locator("#cs-active-list").is_visible()
    assert page.locator("#cs-active-none").is_hidden()
    assert page.locator("#cs-active-sort").inner_text()==sort
    assert page.locator("#cs-clear").is_enabled()

def main():
    assert len(ROWS)==6243
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for width in (390,1440):
            page=browser.new_page(viewport={"width":width,"height":844})
            errors=[]
            requests=[]
            page.on("pageerror",lambda e: errors.append(str(e)))
            page.on("response",lambda r: requests.append(r.status)
                    if "college-search-national.v2.json" in r.url else None)
            page.goto(URL,wait_until="domcontentloaded")
            page.locator("#cs-results-section").wait_for(state="visible",timeout=30000)
            defaults(page)

            page.locator("#cs-name").fill("College")
            active(page,["School name: “College”"])
            assert result_count(page)==sum("college" in r["name"].lower() for r in ROWS)
            clear(page)

            page.locator("#cs-state").select_option("NY")
            active(page,["State or territory: New York (NY)"])
            assert result_count(page)==sum(r["state"]=="NY" for r in ROWS)
            clear(page)

            page.locator("#cs-control").select_option("private_nonprofit")
            active(page,["Institution control: Private nonprofit"])
            assert result_count(page)==sum(r["control"]=="private_nonprofit" for r in ROWS)
            clear(page)

            page.locator("#cs-locale").select_option("rural")
            active(page,["Campus setting: Rural"])
            assert result_count(page)==sum(r["locale"]=="rural" for r in ROWS)
            clear(page)

            page.locator("#cs-size").select_option("5000-14999")
            active(page,["Undergraduate size: 5,000–14,999"])
            assert result_count(page)==sum(
                r["undergraduate_size"] is not None and 5000<=r["undergraduate_size"]<15000
                for r in ROWS)
            clear(page)

            page.locator("#cs-sort").select_option("name-desc")
            assert page.locator("#cs-active-none").is_visible()
            assert page.locator("#cs-active-list").is_hidden()
            assert page.locator("#cs-active-sort").inner_text()=="Sort: School name: Z–A"
            assert result_count(page)==6243
            clear(page)

            page.locator("#cs-name").fill("College")
            page.locator("#cs-state").select_option("NY")
            page.locator("#cs-control").select_option("public")
            page.locator("#cs-locale").select_option("city")
            page.locator("#cs-size").select_option("under-5000")
            page.locator("#cs-sort").select_option("name-desc")
            expected=sum("college" in r["name"].lower() and r["state"]=="NY" and
                r["control"]=="public" and r["locale"]=="city" and
                r["undergraduate_size"] is not None and r["undergraduate_size"]<5000
                for r in ROWS)
            active(page,[
                "School name: “College”","State or territory: New York (NY)",
                "Institution control: Public","Campus setting: City",
                "Undergraduate size: Under 5,000",
            ],sort="Sort: School name: Z–A")
            assert result_count(page)==expected
            assert page.locator(".cs-card").count()==min(24,expected)

            page.locator("#cs-name").fill("QZX_NONEXISTENT_COLLEGE_92871")
            assert result_count(page)==0
            assert page.locator(".cs-card").count()==0
            assert page.locator("#cs-empty").is_visible()
            assert page.locator("#cs-show-more").is_hidden()
            active(page,[
                "School name: “QZX_NONEXISTENT_COLLEGE_92871”",
                "State or territory: New York (NY)","Institution control: Public",
                "Campus setting: City","Undergraduate size: Under 5,000",
            ],sort="Sort: School name: Z–A")
            clear(page)
            assert page.locator("#cs-empty").is_hidden()

            page.locator("#cs-show-more").click()
            page.locator("#cs-show-more").click()
            assert page.locator(".cs-card").count()==72
            assert "showing 72" in page.locator("#cs-result-count").inner_text()
            assert page.locator("#cs-clear").is_enabled()
            assert page.locator("#cs-active-none").is_visible()
            clear(page)

            page.locator("#cs-show-more").click()
            assert page.locator(".cs-card").count()==48
            page.locator("#cs-locale").select_option("city")
            expected=sum(r["locale"]=="city" for r in ROWS)
            assert result_count(page)==expected
            assert page.locator(".cs-card").count()==min(24,expected)
            assert "showing 24" in page.locator("#cs-result-count").inner_text()
            active(page,["Campus setting: City"])
            clear(page)

            # Treat visitor input as text, not markup.
            page.locator("#cs-name").fill("<em>Not a school</em>")
            assert page.locator("#cs-active-list li").count()==1
            assert page.locator("#cs-active-list em").count()==0
            assert "<em>Not a school</em>" in page.locator("#cs-active-list li").inner_text()
            assert result_count(page)==0
            clear(page)

            assert requests==[200],requests
            assert not errors,errors
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
            print("SPRINT2_ACTIVE_SELECTIONS_PASS",json.dumps({
                "width":width,"records":len(ROWS),"individual_filters":5,
                "sort_only":True,"combined_controls":6,"zero_result":True,
                "clear_after_showing_72":True,"filter_after_showing_48":True,
                "data_requests":len(requests),"page_errors":len(errors),
            },sort_keys=True))
            page.close()
        browser.close()

if __name__=="__main__":
    main()
