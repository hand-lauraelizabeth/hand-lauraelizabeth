from pathlib import Path
from playwright.sync_api import sync_playwright
import re
p=Path(__file__).parent
html=(p/'index.html').read_text()
html=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', '', html).replace('<script type="module" src="app.mjs"></script>','')
parts=[]
for name in ['structure-checks.mjs','content-checks.mjs','control-checks.mjs','location.mjs','core.mjs','report-export.mjs','render.mjs','file-input.mjs','download.mjs','app.mjs']:
 s=(p/name).read_text()
 parts.append(re.sub(r'^import .*?;\s*$', '', s, flags=re.M).replace('export function ','function '))
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':320,'height':720})
 page.set_content(html)
 page.add_style_tag(content=(p/'styles.css').read_text())
 page.add_script_tag(content='\n'.join(parts))
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.locator('#source').fill('<html><body><h1>A</h1><h3>B</h3><img><input></body></html>')
 page.locator('#analyze').click()
 for rule in ['page-language','page-title','heading-jump','image-alt-missing','form-name']:
  assert rule in page.locator('#findings').inner_text()
 assert page.locator('#status').get_attribute('role')=='status'
 browser.close()
print('7 FT-10 synthetic smoke assertions passed (injected browser source)')
