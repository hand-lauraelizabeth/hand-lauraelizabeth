from pathlib import Path
from shutil import which
from playwright.sync_api import sync_playwright
src=(Path(__file__).parent/'focus-checks.mjs').read_text().replace('export function ','function ')
cases=[('<div aria-hidden="true"><button>Go</button></div>',1),('<div aria-hidden="true"><button disabled>Go</button></div>',0),('<p aria-hidden="true" tabindex="0">Go</p>',1),('<div aria-hidden="true"><button tabindex="-1">Go</button></div>',0),('<details aria-hidden="true"><summary>Go</summary></details>',1),('<a href="/"><span aria-hidden="true">Icon</span>Go</a>',0)]
with sync_playwright() as pw:
 options={'headless':True}
 if not Path(pw.chromium.executable_path).exists(): options.update(executable_path=which('chromium'),args=['--no-sandbox'])
 b=pw.chromium.launch(**options); page=b.new_page()
 page.add_script_tag(content=src+"; function audit(s){const d=new DOMParser().parseFromString(s,'text/html');const a=[];checkHiddenFocus(d,(rule)=>a.push(rule));return a;}")
 for markup,expected in cases: assert len(page.evaluate('(s)=>audit(s)',markup))==expected
 b.close()
print('6 hidden-focus Chromium checks PASS')
