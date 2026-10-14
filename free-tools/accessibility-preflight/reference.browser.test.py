from pathlib import Path
from shutil import which
from playwright.sync_api import sync_playwright
p=Path(__file__).parent
source=(p/'reference-checks.mjs').read_text().replace('export function ','function ')
cases=[
 ('<a href="#x">Go</a><h2 id="x">Here</h2>',[]),
 ('<a href="#missing">Go</a>',['fragment-target']),
 ('<a href="#%C3%A9">Go</a><h2 id="é">Here</h2>',[]),
 ('<a href="#%E0%A4%A">Go</a>',['fragment-encoding']),
 ('<a href="/other#missing">Other</a>',[]),
 ('<form id="f"></form><input form="f">',[]),
 ('<input form="missing">',['form-owner']),
 ('<input list="missing">',['datalist-target']),
 ('<datalist id="d"></datalist><input list="d">',[]),
 ('<a href="#Case">Go</a><h2 id="case">Here</h2>',['fragment-target'])
]
with sync_playwright() as pw:
 opts={'headless':True}
 if not Path(pw.chromium.executable_path).exists():opts.update(executable_path=which('chromium'),args=['--no-sandbox'])
 b=pw.chromium.launch(**opts)
 page=b.new_page()
 page.add_script_tag(content=source+';function audit(s){const d=new DOMParser().parseFromString(s,"text/html");const a=[];checkDocumentReferences(d,(rule)=>a.push(rule));return a;}')
 for html,expected in cases:
  actual=page.evaluate('(s)=>audit(s)',html)
  assert actual==expected,(html,actual,expected)
 b.close()
print('10 FT-10 reference checks PASS')
