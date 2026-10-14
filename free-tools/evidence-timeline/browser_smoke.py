"""Synthetic Chromium checks. Restricted runtimes inject local source into an about:blank document.
This exercises UI logic, not deployment CSP or a served module graph.
Requires Python Playwright and Chromium.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,re
root=Path(__file__).parent
html=(root/'index.html').read_text()
assert "connect-src 'none'" in html
html=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>','',html)
html=html.replace('<link rel="stylesheet" href="styles.css">','<style>'+(root/'styles.css').read_text()+'</style>')
html=html.replace('<script type="module" src="app.mjs"></script>','')
core=(root/'core.mjs').read_text().replace('export function','function')
app=(root/'app.mjs').read_text().replace("import {normalizeEvidence,exportEvidenceCSV,summary} from './core.mjs';",'')
html=html.replace('</body>','<script>'+core+'\n'+app+'</script></body>')
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(accept_downloads=True,viewport={'width':320,'height':700})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content(html)
 assert page.locator('main').count()==1
 assert page.locator('label[for="sourceId"]').count()==1
 assert page.locator('#csv').is_disabled()
 page.locator('#entry-form button').click()
 assert 'Source ID is required' in page.locator('#error').inner_text()
 assert page.locator('#error').evaluate('(e)=>document.activeElement===e')
 for key,val in [('sourceId','B'),('date','2024-02-29'),('claim','<strong>literal</strong>'),('group','g')]:page.locator('#'+key).fill(val)
 page.locator('#entry-form button').click()
 assert page.locator('#records li').count()==1
 assert page.locator('#records strong').count()==0
 for key,val in [('sourceId','A'),('date','2024-02-28'),('claim','=1+1'),('group','g')]:page.locator('#'+key).fill(val)
 page.locator('#entry-form button').click()
 assert page.locator('#records h3').first.inner_text().startswith('A')
 assert 'A, B' in page.locator('#groups').inner_text()
 with page.expect_download() as d:page.locator('#csv').click()
 assert '"\x27=1+1"' in d.value.path().read_text()
 with page.expect_download() as d:page.locator('#json').click()
 assert json.loads(d.value.path().read_text())['records'][0]['claim']=='=1+1'
 page.locator('#records button').first.click()
 assert page.locator('#records li').count()==1
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 page.evaluate("document.documentElement.style.fontSize='32px'")
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 assert not errors,errors
 browser.close()
print('PASS 15 synthetic Chromium assertions; CSP not exercised')
