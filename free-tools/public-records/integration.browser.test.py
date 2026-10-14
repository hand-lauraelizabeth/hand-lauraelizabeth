"""Synthetic Chromium UI tests; injected source does not verify HTTP/CSP."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import re, json
p=Path(__file__).parent
html=(p/'index.html').read_text()
html=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>','',html)
html=html.replace('<script type="module" src="app.mjs"></script>','')
def module(name):
    code=(p/name).read_text()
    code=re.sub(r'^import .*?;\s*$','',code,flags=re.M)
    return code.replace('export function ','function ').replace('export const ','const ').replace('export async function ','async function ')
script='\n'.join(module(n) for n in ['core.mjs','import.mjs','reopen-ui.mjs','export-ui.mjs','app.mjs'])
checks=0
def check(condition,label):
    global checks
    assert condition,label
    checks+=1
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':320,'height':700},accept_downloads=True)
    page.set_content(html)
    page.add_style_tag(content=(p/'styles.css').read_text())
    page.add_script_tag(content=script)
    check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'320px horizontal overflow')
    check(page.locator('#status').get_attribute('role')=='status','status region')
    page.locator('#request-form [name=id]').fill('  R-1  ')
    page.locator('#request-form [name=agency]').fill('Synthetic Agency')
    page.locator('#request-form [name=description]').fill('<img src=x onerror=alert(1)>')
    page.locator('#request-form button').click()
    check('Added request' in page.locator('#status').inner_text(),'request added')
    check('  R-1  ' in page.locator('#requests').text_content(),'request ID preserved')
    check(page.locator('#requests img').count()==0,'untrusted markup not rendered')
    page.locator('#event-form [name=id]').fill(' EV-1 ')
    page.locator('#event-form [name=requestId]').select_option('  R-1  ')
    page.locator('#event-form [name=date]').fill('2024-02-29')
    page.locator('#event-form [name=sourceId]').fill('  SRC-1  ')
    page.locator('#event-form [name=description]').fill('=1+1')
    page.locator('#event-form button').click()
    check('Added event' in page.locator('#status').inner_text(),'event added')
    check('  SRC-1  ' in page.locator('#events').text_content(),'source ID preserved')
    with page.expect_download() as download:
        page.locator('#save-json').click()
    saved=json.loads(Path(download.value.path()).read_text())
    check(saved['requests'][0]['id']=='  R-1  ','JSON exact request ID')
    check(saved['events'][0]['sourceId']=='  SRC-1  ','JSON exact source ID')
    with page.expect_download() as download:
        page.locator('#save-csv').click()
    csv=Path(download.value.path()).read_text()
    check("'=1+1" in csv,'CSV formula precaution')
    check('<img src=x onerror=alert(1)>' in csv,'CSV literal text preserved')
    page.evaluate('document.documentElement.style.fontSize="200%"')
    check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'enlarged text horizontal overflow')
    browser.close()
print(f'{checks} FT-09 synthetic Chromium integration assertions PASS (served CSP unverified)')
