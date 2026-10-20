from pathlib import Path
from playwright.sync_api import sync_playwright
p=Path(__file__).parent
source=(p/'relationship-checks.mjs').read_text().replace('export function ','function ')
cases=[
 ('<button aria-labelledby="missing"></button>','unresolved-id-reference'),
 ('<input aria-describedby="missing">','unresolved-id-reference'),
 ('<input aria-controls="missing">','unresolved-id-reference'),
 ('<input aria-activedescendant="one two">','single-id-reference'),
 ('<input aria-labelledby="  ">','empty-id-reference'),
 ('<span id="x"></span><input aria-labelledby="x x">','repeated-id-reference'),
 ('<label for="missing">Name</label>','label-target'),
 ('<div id="x"></div><label for="x">Name</label>','label-target'),
 ('<table><tr><td headers="missing">A</td></tr></table>','table-header-reference'),
 ('<button aria-label="Submit">Send</button>','label-in-name'),
 ('<iframe></iframe>','iframe-title')]
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=b.new_page()
 page.goto('about:blank')
 page.add_script_tag(content=source+"""
 function audit(s){const doc=new DOMParser().parseFromString(s,'text/html');const result=[];checkRelationships(doc,(rule)=>result.push(rule));return result;}
 """)
 checks=0
 for html,expected in cases:
  assert expected in page.evaluate('(s)=>audit(s)',html),(expected,html)
  checks+=1
 good='<span id="label" hidden>Valid</span><input id="x" aria-labelledby="label"><label for="x">Name</label><table><tr><th id="h">Header</th><td headers="h">A</td></tr></table><iframe title="Preview"></iframe>'
 assert page.evaluate('(s)=>audit(s)',good)==[]
 checks+=1
 b.close()
print(f'{checks} FT-10 ARIA relationship browser checks passed')
