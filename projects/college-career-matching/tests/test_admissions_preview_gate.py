"""Independent Chromium interaction and accessibility checks for the review-only admissions preview."""
from pathlib import Path
from playwright.sync_api import sync_playwright

PAGE = Path(__file__).resolve().parents[1] / "admissions-evidence-review.html"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(PAGE.as_uri())
        assert page.get_by_role("heading", name="College + Career Matcher: admissions evidence preview").is_visible()
        select = page.get_by_label("Choose a Hunter nursing pathway")
        for value, expected in [
            ("generic", "Generic BS in Nursing"),
            ("accelerated", "Accelerated Second-Degree BS (A2D)"),
            ("rn", "RN-to-BS completion"),
        ]:
            select.select_option(value)
            assert expected in page.locator("#status").inner_text()
            assert expected == page.locator("#name").inner_text()
            assert page.locator("#source").get_attribute("href").startswith("https://www.hunter.cuny.edu/")
        assert "not independently established" in page.locator("#requirement").inner_text()
        assert page.get_by_role("table", name="Hunter nursing pathway distinctions").is_visible()
        assert page.locator("table tbody tr").count() == 3
        select.focus()
        assert select.evaluate("(el) => document.activeElement === el")
        # axe-core is installed through the npm package in the dedicated workflow step.
        axe = Path("/tmp/matcher-axe/node_modules/axe-core/axe.min.js")
        assert axe.is_file(), "axe-core must be installed; never silently skip accessibility checks"
        page.add_script_tag(content=axe.read_text())
        results = page.evaluate("""async () => await axe.run(document, {
          runOnly: {type:'tag', values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}
        })""")
        severe = [v for v in results["violations"] if v["impact"] in ("serious", "critical")]
        assert not severe, [(v["id"], v["impact"]) for v in severe]
        print("PASS: three pathway interactions, source links, mobile table, keyboard focus, axe serious/critical=0")
        browser.close()

if __name__ == "__main__":
    main()
