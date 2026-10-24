"""Synthetic DOM-injected browser regression: source changes invalidate prior exports.

Requires Playwright and Chromium. This is not a served HTTP/CSP or native AT test.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import re
import os

source_path=Path(__file__).parent/'app.mjs'
app=source_path.read_text(encoding='utf-8')
app=re.sub(r'^import .*?;\s*$', '', app, flags=re.M)
html='''<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>
<input id="html-file" type="file"><textarea id="source"></textarea><button id="analyze">Analyze HTML</button>
<button id="download-json">Download JSON</button><button id="download-csv">Download CSV</button>
<p id="status" role="status"></p><p id="summary"></p><ol id="findings"></ol></body></html>'''
stubs='''
window.saved=[];
function inspectDocument(doc){return {findings:[{rule:'synthetic',message:doc.body.textContent.trim()}]};}
function renderFindings(report,findings,summary){const li=document.createElement('li');li.textContent=report.findings[0].message;findings.append(li);summary.textContent='1 finding';}
function bindHTMLFile(input,target,status){input.addEventListener('change',async()=>{const f=input.files?.[0];if(f){target.value=await f.text();status.textContent='HTML loaded locally.';}});}
function saveLocal(name,mime,content){window.saved.push({name,mime,content});}
function exportFindingsCSV(findings){return findings[0].message;}
'''
count=0
with sync_playwright() as pw:
    engine=os.getenv('FT10_BROWSER','chromium')
    options={'headless':True}
    if engine=='chromium' and Path('/usr/bin/chromium').exists() and os.getenv('FT10_USE_SYSTEM_CHROMIUM')=='1':
        options.update(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    browser=getattr(pw,engine).launch(**options)
    page=browser.new_page(viewport={'width':320,'height':700})
    page.set_content(html)
    page.add_script_tag(content=stubs+'\n'+app)
    page.locator('#source').fill('<h1>First</h1>')
    page.locator('#analyze').click()
    assert page.locator('#findings li').count()==1;count+=1
    page.locator('#download-json').click()
    assert len(page.evaluate('window.saved'))==1;count+=1
    page.locator('#source').fill('<h1>Second</h1>')
    assert page.locator('#findings li').count()==0;count+=1
    assert 'Previous findings cleared' in page.locator('#summary').inner_text();count+=1
    page.locator('#download-json').click()
    assert len(page.evaluate('window.saved'))==1;count+=1
    assert 'Analyze HTML first' in page.locator('#status').inner_text();count+=1
    page.locator('#analyze').click()
    page.locator('#download-csv').click()
    assert page.evaluate('window.saved.at(-1).content')=='Second';count+=1
    page.locator('#html-file').set_input_files({'name':'third.html','mimeType':'text/html','buffer':b'<h1>Third</h1>'})
    assert page.locator('#findings li').count()==0;count+=1
    page.locator('#download-csv').click()
    assert len(page.evaluate('window.saved'))==2;count+=1
    page.wait_for_function("document.querySelector('#source').value.includes('Third')")
    page.locator('#analyze').click()
    page.locator('#download-json').click()
    assert 'Third' in page.evaluate('window.saved.at(-1).content');count+=1
    page.locator('#source').fill(' ')
    page.locator('#analyze').click()
    assert page.locator('#findings li').count()==0;count+=1
    assert 'Cannot analyze' in page.locator('#status').inner_text();count+=1
    page.locator('#download-json').click()
    assert len(page.evaluate('window.saved'))==3;count+=1
    browser.close()
print(f'PASS: {count} FT-10 {os.getenv("FT10_BROWSER","chromium")} synthetic browser assertions: edit, replace, reanalyze, invalid source, JSON/CSV fail-closed')
