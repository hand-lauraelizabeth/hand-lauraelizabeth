"""Hosted-preview-equivalent Chromium interaction and accessibility smoke tests."""
import pathlib
from playwright.sync_api import sync_playwright

URL = pathlib.Path(__file__).with_name("admissions-evidence-review-preview.html").resolve().as_uri()

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={"width":390,"height":844})
        errors=[]
        page.on("pageerror",lambda e: errors.append(str(e)))
        page.goto(URL)
        assert page.get_by_role("heading",name="College + Career Matcher: admissions evidence").is_visible()
        page.locator("#check-cycle").check()
        assert "1 of 3" in page.locator("#check-status").inner_text()
        page.locator("#route").select_option("accelerated")
        assert "0 of 3" in page.locator("#check-status").inner_text()
        page.locator("#check-prerequisites").check()
        page.locator("#route").select_option("generic")
        assert page.locator("#check-cycle").is_checked()
        page.locator("#clear-all-checks").click()
        page.locator("#route").select_option("accelerated")
        assert not page.locator("#check-prerequisites").is_checked()
        page.locator("#route").select_option("rn")
        with page.expect_download() as download:
            page.locator("#download-evidence").click()
        assert "rn-nursing-pathway" in download.value.suggested_filename
        assert not errors,errors
        # Storage-disabled behavior: both sessionStorage methods throw.
        page.add_init_script("""() => {
          Object.defineProperty(window,'sessionStorage',{get(){throw Error('disabled')}});
        }""")
        page.reload()
        page.locator("#check-cycle").check()
        assert "1 of 3" in page.locator("#check-status").inner_text()
        assert "unavailable" in page.locator("#check-status").inner_text()
        page.locator("#clear-all-checks").click()
        assert "0 of 3" in page.locator("#check-status").inner_text()
        assert not errors,errors
        browser.close()
    print("PASS: pathway state, privacy clear, download, storage-disabled fallback, mobile Chromium")

if __name__=="__main__":main()
