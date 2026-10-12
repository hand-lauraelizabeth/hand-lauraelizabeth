"""Review-only browser smoke against real NCES IPEDS program shards, never fixtures."""
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8767/program-evidence-review.html'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for width in (390, 1440):
        page = browser.new_page(viewport={'width': width, 'height': 844})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        # The external Scorecard name overlay is optional. Never invent names.
        page.route('https://cdn.jsdelivr.net/**', lambda route: route.abort())
        page.goto(URL, wait_until='domcontentloaded')
        assert 'historical program completions' in page.locator('h1').inner_text().lower()
        assert 'not a list of programs currently offered' in page.locator('header').inner_text().lower()
        page.locator('#program-query').fill('51.3801')
        page.locator('#award-level').select_option('5')
        page.locator('#program-search').click()
        page.wait_for_function(
            "document.querySelector('#status').textContent.includes('historical program/award records match')",
            timeout=60000,
        )
        assert page.locator('.result').count() > 0
        assert 'Current offering status is not verified' in page.locator('#status').inner_text()
        assert 'CIP 2020 51.3801' in page.locator('.result').first.inner_text()
        assert "Bachelor's degree" in page.locator('.result').first.inner_text()
        assert 'Historical evidence only' in page.locator('.result').first.inner_text()
        assert not errors, errors
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'
        print('Program evidence browser PASS:', width, page.locator('#results-title').inner_text())
        page.close()
    browser.close()