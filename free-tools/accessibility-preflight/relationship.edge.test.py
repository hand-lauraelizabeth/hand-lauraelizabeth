# FT-10 ARIA relationship edge cases
# Run: python relationship.edge.test.py
from pathlib import Path
from playwright.sync_api import sync_playwright
source=(Path(__file__).parent/'relationship-checks.mjs').read_text().replace('export function checkRelationships','function checkRelationships')
cases=[
('<label for="x">Name</label><input id="x">',[]),
('<label for="x">Name</label><input id="x" type="hidden">',['label-target']),
('<input aria-describedby="unknown">',['unresolved-id-reference']),
('<input aria-describedby="note note"><span id="note">Info</span>',['repeated-id-reference']),
('<table><tr><th id="h">Header</th><td headers="h">Value</td></tr></table>',[]),
('<table><tr><td headers="missing">Value</td></tr></table>',['table-header-reference']),
('<button aria-label="Save document">Save</button>',[]),
('<button aria-label="Submit document">Save</button>',['label-in-name']),
('<iframe title="Chart"></iframe>',[]),
('<iframe></iframe>',['iframe-title']),
('<input aria-labelledby="abc"><span id="abc">label</span>',[]),
('<input aria-activedescendant="a b">',['single-id-reference','unresolved-id-reference'])
]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 page=browser.new_page()
 for markup, expected in cases:
  actual=page.evaluate('''([source,markup]) => { const doc=new DOMParser().parseFromString(markup,'text/html'); const results=[]; const add=code=>results.push(code); (new Function('doc','add',source+'; checkRelationships(doc,add);'))(doc,add); return results; }''',[source,markup])
  assert all(code in actual for code in expected),(markup,expected,actual)
  if not expected: assert actual==[],(markup,actual)
 print('12 synthetic relationship edge cases PASS')
 browser.close()
