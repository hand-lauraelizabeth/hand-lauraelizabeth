"""Synthetic Chromium smoke test; does not verify HTTP loading or deployed CSP."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,re
p=Path(__file__).parent
html=(p/'index.html').read_text()
assert "connect-src 'none'" in html
html=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>','',html)
html=html.replace('<link rel="stylesheet" href="styles.css">','<style>'+(p/'styles.css').read_text()+'</style>')
html=html.replace('<script type="module" src="app.mjs"></script>','')
core=(p/'core.mjs').read_text().replace('export function normalizeEvidence','function oldNormalize').replace('export function','function')
exact=(p/'exact-core.mjs').read_text().replace('export function','function')
imp=(p/'json-import.mjs').read_text().replace("import {normalizeExact} from './exact-core.mjs';",'').replace('export const','const').replace('export function','function').replace('export async function','async function')
app=re.sub(r"^import \{[^\n]+\} from '[^']+';\n?",'',(p/'app.mjs').read_text(),flags=re.M).replace('normalizeEvidence(','normalizeExact(')
html=html.replace('</body>','<script>'+core+'\n'+exact+'\n'+imp+'\n'+app+'</script></body>')
count=0
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(accept_downloads=True,viewport={'width':375,'height':720})
 errors=[];requests=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:requests.append(r.url))
 page.set_content(html)
 assert not errors;count+=1
 assert page.locator('#resume-json').count()==1;count+=1
 assert page.locator('#csv').is_disabled();count+=1
 for key,value in [('sourceId','  A-001  '),('date','2024-02-29'),('claim','<b>literal</b>')]:page.locator('#'+key).fill(value)
 page.locator('#entry-form button').click()
 assert page.locator('#records h3').text_content().startswith('  A-001  ');count+=1
 assert page.locator('#records b').count()==0;count+=1
 with page.expect_download() as d:page.locator('#json').click()
 assert json.loads(d.value.path().read_text())['records'][0]['sourceId']=='  A-001  ';count+=1
 page.locator('#resume-json').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':b'\xff'})
 assert 'Invalid UTF-8' in page.locator('[aria-labelledby="resume-heading"] p[role="status"]').inner_text();count+=1
 assert page.locator('#records li').count()==1;count+=1
 good=json.dumps({'schema':'evidence-timeline-v1','records':[{'sourceId':'  B-002  ','date':'2023-01-02','claim':'=1+1','status':'reported','kind':'source','group':''}]}).encode()
 page.once('dialog',lambda d:d.dismiss())
 page.locator('#resume-json').set_input_files({'name':'good.json','mimeType':'application/json','buffer':good})
 assert page.locator('#records h3').text_content().startswith('  A-001  ');count+=1
 page.once('dialog',lambda d:d.accept())
 page.locator('#resume-json').set_input_files({'name':'good.json','mimeType':'application/json','buffer':good})
 assert page.locator('#records h3').text_content().startswith('  B-002  ');count+=1
 with page.expect_download() as d:page.locator('#csv').click()
 assert '"\'=1+1"' in d.value.path().read_text();count+=1
 page.evaluate("document.body.style.zoom='2'")
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');count+=1
 assert not requests and not errors;count+=1
 browser.close()
print(f'PASS {count} synthetic Chromium checks; deployed CSP unverified')
