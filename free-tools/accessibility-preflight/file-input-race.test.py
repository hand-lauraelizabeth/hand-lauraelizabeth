"""FT-10 synthetic browser regression: async file read cannot replace later typed text.
Run: python file-input-race.test.py (requires Playwright and Chromium).
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

source=(Path(__file__).parent/'file-input.mjs').read_text().replace('export function ','function ')
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page()
    page.set_content('<input id="f" type="file"><textarea id="s"></textarea><p id="status"></p>')
    page.add_script_tag(content=source+'''
    const f=document.querySelector('#f'),s=document.querySelector('#s'),status=document.querySelector('#status');
    bindHTMLFile(f,s,status);
    window.makePending=(name='sample.html')=>{
      let finish;
      const selected={name,size:20,arrayBuffer:()=>new Promise(resolve=>finish=resolve)};
      Object.defineProperty(f,'files',{configurable:true,get:()=>[selected]});
      f.dispatchEvent(new Event('change'));
      return bytes=>finish(new TextEncoder().encode(bytes).buffer);
    };
    ''')
    # Complete normal async read.
    page.evaluate('''async()=>{const finish=makePending();finish('<h1>File</h1>');await new Promise(r=>setTimeout(r,0));}''')
    assert page.locator('#s').input_value()=='<h1>File</h1>'
    assert 'loaded locally' in page.locator('#status').inner_text()
    # Later typing must cancel a pending file read.
    page.evaluate('''async()=>{const finish=makePending();const s=document.querySelector('#s');s.value='<h1>Typed</h1>';s.dispatchEvent(new Event('input',{bubbles:true}));finish('<h1>Old file</h1>');await new Promise(r=>setTimeout(r,0));}''')
    assert page.locator('#s').input_value()=='<h1>Typed</h1>'
    # A later file selection wins over an earlier pending read.
    page.evaluate('''async()=>{const first=makePending();const second=makePending();second('<h1>New</h1>');first('<h1>Old</h1>');await new Promise(r=>setTimeout(r,0));}''')
    assert page.locator('#s').input_value()=='<h1>New</h1>'
    # Malformed UTF-8 must not replace the current document.
    page.evaluate('''async()=>{const f=document.querySelector('#f');
      const selected={name:'bad.html',size:2,arrayBuffer:async()=>new Uint8Array([0xc3,0x28]).buffer};
      Object.defineProperty(f,'files',{configurable:true,get:()=>[selected]});
      f.dispatchEvent(new Event('change'));await new Promise(r=>setTimeout(r,0));}''')
    assert page.locator('#s').input_value()=='<h1>New</h1>'
    assert 'File rejected:' in page.locator('#status').inner_text()
    print('4 browser assertions PASS: valid read, typed text wins, latest file wins, invalid UTF-8 rejected')
    browser.close()
