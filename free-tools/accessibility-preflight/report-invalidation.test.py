"""Synthetic browser checks for stale-report invalidation (not CSP verification)."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import re
p=Path(__file__).parent
html=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>','',(p/'reference-preview.html').read_text()).replace('<script type="module" src="app-reference.mjs"></script>','')
names='structure-checks content-checks control-checks relationship-checks focus-checks location core focus-extended reference-checks reference-extended report-export render file-input download app-reference'.split()
scripts='\n'.join(re.sub(r'^import .*?;\s*$','',(p/(n+'.mjs')).read_text(),flags=re.M).replace('export function ','function ') for n in names)
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=b.new_page(accept_downloads=True)
 page.set_content(html);page.add_script_tag(content=scripts)
 page.locator('#source').fill('<h1>Title</h1><a href="#missing">Link</a>')
 page.locator('#analyze').click()
 assert 'fragment-target' in page.locator('#findings').inner_text()
 page.locator('#source').fill('<h1>Changed</h1>')
 assert page.locator('#findings li').count()==0
 page.locator('#download-json').click()
 assert 'Analyze HTML first' in page.locator('#status').inner_text()
 page.locator('#analyze').click()
 assert 'fragment-target' not in page.locator('#findings').inner_text()
 b.close()
print('4 report-invalidation browser assertions PASS')
