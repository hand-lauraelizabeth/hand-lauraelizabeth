"""Synthetic UI integration; injected modules do not verify served CSP."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import re
p=Path(__file__).parent
html=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', '', (p/'reference-preview.html').read_text()).replace('<script type="module" src="app-reference.mjs"></script>','')
parts=[]
for name in ['structure-checks.mjs','content-checks.mjs','control-checks.mjs','relationship-checks.mjs','focus-checks.mjs','reference-checks.mjs','location.mjs','core.mjs','focus-extended.mjs','reference-extended.mjs','report-export.mjs','render.mjs','file-input.mjs','download.mjs','app-reference.mjs']:
 source=(p/name).read_text()
 parts.append(re.sub(r'^import .*?;\s*$', '', source, flags=re.M).replace('export function ','function '))
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':320,'height':700})
 errors=[]
 page.on('pageerror',lambda error: errors.append(str(error)))
 page.set_content(html)
 page.add_style_tag(content=(p/'styles.css').read_text())
 page.add_script_tag(content='\n'.join(parts))
 page.locator('#source').fill('<html lang="en"><head><title>Example</title></head><body><h1>Heading</h1><div aria-hidden="true"><button>Save</button></div><button aria-labelledby="missing">Send</button><a href="#absent">Skip</a></body></html>')
 page.locator('#analyze').click()
 report=page.locator('#findings').inner_text()
 assert 'aria-hidden-focus' in report
 assert 'unresolved-id-reference' in report
 assert 'fragment-target' in report
 assert not errors,errors
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 page.evaluate('document.documentElement.style.fontSize="200%"')
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 assert page.locator('#status').get_attribute('role')=='status'
 page.locator('#source').fill('<html lang="en"><head><title>Example</title></head><body><h1>Heading</h1><div aria-hidden="true"><button disabled>Save</button></div></body></html>')
 page.locator('#analyze').click()
 assert 'aria-hidden-focus' not in page.locator('#findings').inner_text()
 browser.close()
print('9 FT-10 reference-preview integrated Chromium assertions PASS (injected source)')
