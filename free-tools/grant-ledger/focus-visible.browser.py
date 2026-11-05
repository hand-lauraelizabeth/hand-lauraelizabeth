"""Keyboard and error-focus regression for the local grant ledger.

Requires Python Playwright and Chromium; synthetic inputs only.
"""
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parent
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=shutil.which('chromium') or pw.chromium.executable_path,headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':320,'height':900})
    page.set_content('<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><main id="root"><h1>Grant ledger</h1></main></body></html>')
    page.add_style_tag(content=(root/'styles.css').read_text())
    m={n:(root/n).read_text() for n in ('core.mjs','view.mjs','render.mjs','app.mjs')}
    page.evaluate("""async m=>{
      const mk=t=>URL.createObjectURL(new Blob([t],{type:'text/javascript'}));
      const c=mk(m['core.mjs']),v=mk(m['view.mjs']);
      const r=mk(m['render.mjs'].replace("'./core.mjs'",JSON.stringify(c)));
      const a=mk(m['app.mjs'].replace("'./core.mjs'",JSON.stringify(c)).replace("'./view.mjs'",JSON.stringify(v)).replace("'./render.mjs'",JSON.stringify(r)));
      await import(a);
    }""",m)
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.name')=='awardId'
    page.get_by_label('Category ID').fill('CAT-1')
    page.get_by_label('Category label').fill('Synthetic')
    page.get_by_label('Planned budget ($)').fill('invalid')
    page.locator('#categoryForm button[type=submit]').click()
    assert page.evaluate('document.activeElement.id')=='error'
    assert page.locator('#error').get_attribute('role')=='alert'
    outline=page.locator('#error').evaluate("e=>getComputedStyle(e).outline")
    assert 'solid 3px' in outline,outline
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.add_style_tag(content='*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    browser.close()
print('PASS: keyboard focus, alert focus ring, 320px reflow and text-spacing')
