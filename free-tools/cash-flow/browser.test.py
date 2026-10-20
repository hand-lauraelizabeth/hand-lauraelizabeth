from pathlib import Path
import re
from playwright.sync_api import sync_playwright
root=Path(__file__).parent
html=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', '', (root/'index.html').read_text()).replace('<script type="module" src="app.mjs"></script>','').replace('<link rel="stylesheet" href="style.css">','')
engine=(root/'engine.mjs').read_text().replace('export const','const').replace('export function','function')
engine='(()=>{'+engine+'\nwindow.FT04={parseCents,formatCents,dateUTC,project,exportCSV};})()'
app=(root/'app.mjs').read_text().replace("import {parseCents,formatCents,dateUTC,project,exportCSV} from './engine.mjs';","const {parseCents,formatCents,dateUTC,project,exportCSV}=window.FT04;")
checks=0
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':320,'height':760})
 page.set_content(html)
 page.add_style_tag(content=(root/'style.css').read_text())
 page.add_script_tag(content=engine)
 page.add_script_tag(content=app)
 assert page.locator('#export').is_disabled();checks+=1
 page.locator('#calculate').click()
 assert page.locator('#results tr').count()==32;checks+=1
 assert page.locator('#export').is_enabled();checks+=1
 page.locator('#event-id').fill('rent')
 page.locator('#event-label').fill('=FORMULA')
 page.locator('#event-amount').fill('-50.00')
 page.locator('#event-date').fill('2026-10-16')
 page.locator('#event-form button').click()
 assert 'rent' in page.locator('#events').inner_text();checks+=1
 assert page.locator('#export').is_disabled();checks+=1
 page.locator('#calculate').click()
 assert '50.00' in page.locator('#summary').inner_text();checks+=1
 page.locator('#shift-id').select_option('rent')
 page.locator('#shift-days').fill('1')
 page.locator('#calculate').click()
 assert 'scenario minimum' in page.locator('#summary').inner_text();checks+=1
 assert page.locator('#results tr').count()==32;checks+=1
 assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth');checks+=1
 page.evaluate("document.documentElement.style.fontSize='200%'")
 assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth');checks+=1
 page.locator('#opening').fill('1.234')
 assert page.locator('#export').is_disabled();checks+=1
 page.locator('#calculate').click()
 assert 'up to two cents' in page.locator('#error').inner_text();checks+=1
 assert page.locator('#export').is_disabled();checks+=1
 page.locator('#opening').fill('100.00')
 page.locator('#calculate').click()
 with page.expect_download() as info:page.locator('#export').click()
 csv=info.value.path().read_text()
 assert "'=FORMULA" in csv;checks+=1
 assert csv.startswith('"Date"');checks+=1
 page.locator('#events button').click()
 assert 'No events' in page.locator('#events').inner_text();checks+=1
 assert page.locator('#export').is_disabled();checks+=1
 browser.close()
print(f'{checks} FT-04 synthetic Chromium UI assertions PASS (injected source; CSP not verified)')
