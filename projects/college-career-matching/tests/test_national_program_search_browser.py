"""Real-data Chromium validation of lazy national IPEDS program search."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
URL="http://127.0.0.1:8766/college-search-sprint3.html"
DATA_DIR=ROOT/"data/programs/ipeds2025"
MANIFEST=json.loads((DATA_DIR/"programs.manifest.v1.json").read_text())
assert MANIFEST["counts"]["joined_program_award_records"]==235330
INDEX={}
for shard in MANIFEST["shards"]:
    part=json.loads((DATA_DIR/shard["file"]).read_text())
    INDEX.update(part["institutions"])
assert len(INDEX)==5658
TITLES=json.loads((DATA_DIR/"cip2020-titles.json").read_text())
OBSERVED={row[0] for rows in INDEX.values() for row in rows}
assert len(TITLES)==2325 and len(OBSERVED)==1591
UNREPORTED_CIP=sorted(set(TITLES)-OBSERVED)[0]
CIP="513801"

def run(browser,width):
    page=browser.new_page(viewport={"width":width,"height":850})
    errors=[];program_requests=[]
    page.on("pageerror",lambda err:errors.append(str(err)))
    page.on("request",lambda request:program_requests.append(request.url) if "data/programs/ipeds2025" in request.url else None)
    page.goto(URL,wait_until="domcontentloaded")
    page.wait_for_function("document.querySelector('#cs-result-count')?.textContent.includes('6,243 schools')",timeout=30000)
    assert not program_requests,"Program data loaded before visitor requested it"
    panel=page.locator("#cs-program-details")
    assert not panel.evaluate("(x)=>x.open")
    assert page.locator("#cs-program-query").is_disabled()
    assert page.locator("#cs-testing-details").count()==1
    # Native details/summary must open from the keyboard without a mouse.
    panel.locator("summary").focus()
    panel.locator("summary").press("Enter")
    assert panel.evaluate("(x)=>x.open"), "Keyboard Enter must expand program controls"
    page.wait_for_function("document.querySelector('#cs-program-status')?.textContent.includes('5,658 of 6,243')",timeout=90000)
    assert len(program_requests)>=15,(len(program_requests),program_requests)
    assert page.locator("#cs-program-query").is_enabled()
    # People enter familiar major names, occupations, abbreviations, and CIP codes.
    # Search suggestions are code-linked, not assertions of licenses or exact credentials.
    query=page.locator("#cs-program-query")
    # Screen-reader announcements and instructions must remain discoverable.
    assert page.locator("#cs-program-status").get_attribute("role")=="status"
    assert page.locator("#cs-program-status").get_attribute("aria-live")=="polite"
    described=query.get_attribute("aria-describedby").split()
    assert {"cs-program-status","cs-program-help"}.issubset(set(described))
    assert page.locator("#cs-program-options").get_attribute("aria-label")=="Matching fields of study"
    # Common two-character abbreviations should not match incidental substrings.
    for typed,count,first_cip in [("IT",3,"11.0103"),("AI",1,"11.0102"),("HR",1,"52.1001"),
                                  ("PR",1,"09.0902"),("RN",1,"51.3801")]:
        query.fill(typed)
        options=page.locator("#cs-program-options button")
        assert options.count()==count,(typed,options.count(),count)
        assert "CIP "+first_cip in options.first.inner_text(),(typed,options.first.inner_text())
    query.fill("nu")
    assert page.locator("#cs-program-options button").count()==0
    assert "at least three letters" in page.locator("#cs-program-status").inner_text()
    # Reserved federal placeholders remain searchable by literal CIP, but
    # are not selectable or presented as active school programs.
    query.fill("Reserved")
    assert page.locator("#cs-program-options button").count()==0
    query.fill("CIP 12.0580")
    reserved=page.locator("#cs-program-options button")
    assert reserved.count()==1
    assert reserved.first.is_disabled()
    assert "not a field of study" in page.locator("#cs-program-status").inner_text()
    assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools")
    query.focus()
    query.press("Tab")
    assert not reserved.first.evaluate("(e)=>document.activeElement===e"), "Disabled reserved code received focus"
    query.focus()
    for typed,code in [
        ("nurse","51.3801"),
        ("BSN","51.3801"),
        ("LPN","51.3901"),
        ("coding","11.0201"),
        ("HR","52.1001"),
        ("CIP 51.3801","51.3801"),
        ("51.3801","51.3801"),
    ]:
        query.fill(typed)
        opts=page.locator("#cs-program-options button")
        assert opts.count()>0,(typed,"No suggestions")
        assert "CIP "+code in opts.first.inner_text(),(typed,opts.first.inner_text())
        assert "Classification match" in opts.first.inner_text() or "Common-language match" in opts.first.inner_text()
    # The full federal taxonomy stays searchable even when the historical
    # IPEDS snapshot has no matched completion records for a given category.
    query.fill("CIP "+UNREPORTED_CIP[:2]+"."+UNREPORTED_CIP[2:])
    missing=page.locator("#cs-program-options button").first
    assert "CIP "+UNREPORTED_CIP[:2]+"."+UNREPORTED_CIP[2:] in missing.inner_text()
    assert "No matching 2024–25 completions" in missing.inner_text()
    missing.click()
    assert page.locator("#cs-result-count").inner_text().startswith("0 schools")
    assert "Current offerings are unverified" in page.locator("#cs-program-status").inner_text()
    page.locator("#cs-program-remove").click()
    assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools")
    query.fill("UX design")
    assert page.locator("#cs-program-options button").count()>0
    assert "Related subject" in page.locator("#cs-program-options").inner_text()
    # ArrowDown and Escape are usable with the keyboard.
    query.fill("nurse")
    query.press("ArrowDown")
    first_suggestion=page.locator("#cs-program-options button").first
    assert first_suggestion.evaluate("(e)=>document.activeElement===e")
    first_suggestion.press("Enter")
    assert page.locator("#cs-program-chosen").is_visible(), "Enter must select a field"
    assert "51.3801" in page.locator("#cs-program-choice").inner_text()
    page.locator("#cs-program-remove").focus()
    page.locator("#cs-program-remove").press("Enter")
    assert not page.locator("#cs-program-chosen").is_visible()
    assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools")
    query.fill("nurse")
    query.focus()
    query.press("Escape")
    assert page.locator("#cs-program-options button").count()==0
    page.locator("#cs-program-query").fill("Registered Nursing")
    assert page.locator("#cs-program-options button").count()>0
    page.locator("#cs-program-options button").filter(has_text="CIP 51.3801").first.click()
    # Editing a previously chosen term clears that old selection before suggesting a new one.
    query.fill("coding")
    assert "Historical field of study" not in page.locator("#cs-active-list").inner_text()
    assert page.locator("#cs-program-options button").count()>0
    query.fill("Registered Nursing")
    page.locator("#cs-program-options button").filter(has_text="CIP 51.3801").first.click()

    expected=sum(any(row[0]==CIP for row in rs) for rs in INDEX.values())
    actual=int(page.locator("#cs-result-count").inner_text().split()[0].replace(",",""))
    assert actual==expected,(actual,expected)
    assert expected>0
    assert "Reported 2024–25 completions" in page.locator(".cs-card").first.inner_text()
    assert page.locator(".cs-card-program a").first.get_attribute("href").endswith("/C2025_A.zip")
    assert "active historical program setting" in page.locator("#cs-program-active").inner_text()
    page.locator("#cs-award-level").select_option("5")
    expected=sum(any(row[0]==CIP and row[1]=="5" for row in rs) for rs in INDEX.values())
    actual=int(page.locator("#cs-result-count").inner_text().split()[0].replace(",",""))
    assert actual==expected,(actual,expected)
    assert "2 active historical program settings" in page.locator("#cs-program-active").inner_text()
    panel.locator("summary").click()
    assert not panel.evaluate("(x)=>x.open")
    assert int(page.locator("#cs-result-count").inner_text().split()[0].replace(",",""))==expected
    # Other filters still work jointly with the program selection.
    page.locator("#cs-state").select_option("NY")
    assert int(page.locator("#cs-result-count").inner_text().split()[0].replace(",",""))<=expected
    page.locator("#cs-clear").click()
    assert page.locator("#cs-result-count").inner_text().startswith("6,243 schools")
    assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")
    assert not errors,errors
    print("PROGRAM_UI_PASS",width,"program",CIP,"joined_institutions",len(INDEX))
    page.close()

def corrupted_shard_test(browser):
    page=browser.new_page(viewport={"width":390,"height":850})
    page.route("**/programs-00.json",lambda route:route.fulfill(status=200,body='{"schema_version":"1.0","institutions":[]}'))
    page.goto(URL)
    page.wait_for_function("document.querySelector('#cs-result-count')?.textContent.includes('6,243 schools')",timeout=30000)
    page.locator("#cs-program-details summary").click()
    page.wait_for_function("document.querySelector('#cs-program-retry')?.hidden===false",timeout=90000)
    assert page.locator("#cs-program-query").is_disabled()
    page.locator("#cs-name").fill("Columbia")
    assert int(page.locator("#cs-result-count").inner_text().split()[0].replace(",",""))>0
    print("CORRUPT_PROGRAM_SHARD_FAILS_CLOSED")
    page.close()

if __name__=="__main__":
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for width in (390,1440):run(browser,width)
        corrupted_shard_test(browser)
        browser.close()
