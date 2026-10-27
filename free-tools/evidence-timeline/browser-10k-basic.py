"""Synthetic Chromium 10k import/export regression; DOM-injected, not HTTP/CSP QA."""
import json, os, re
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
N=10000
rows=[{'sourceId':f'{i:06d}','date':f'2026-10-{i%28+1:02d}','claim':f'Synthetic record {i}',
       'status':('reported','corroborated','disputed','unresolved')[i%4], 'kind':'source', 'group':f'g{i//2}'} for i in range(N)]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_BIN','/usr/bin/chromium'),args=['--no-sandbox'])
 page=b.new_page(viewport={'width':320,'height':700},accept_downloads=True)
 page.on('dialog',lambda d:d.accept())
 html=(ROOT/'index.html').read_text()
 html=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>','',html)
 html=html.replace('<script type="module" src="app.mjs"></script>','').replace('<link rel="stylesheet" href="styles.css">','')
 page.set_content(html)
 page.add_style_tag(content=(ROOT/'styles.css').read_text())
 scripts=[]
 for name in ('exact-core.mjs','core.mjs','safe-export.mjs','json-import.mjs','import-feedback.mjs','replacement-preview.mjs','review-filter.mjs','source-id-find.mjs','group-find.mjs','group-summary.mjs','edit-group.mjs','reclassify.mjs','undo-status.mjs','app.mjs'):
  body=re.sub(r'^import .*?;\s*$','',(ROOT/name).read_text(),flags=re.M)
  scripts.append(re.sub(r'^export ','',body,flags=re.M))
 page.add_script_tag(content='\n'.join(scripts))
 assert page.evaluate("typeof csvExportRisk === 'function'"), 'CSV safety module available in DOM fixture'
 assert page.evaluate("typeof filterByGroupLabel === 'function'"), 'Group search module available in DOM fixture'
 assert page.evaluate("typeof formatGroupSummary === 'function'"), 'Group summary module available in DOM fixture'
 page.locator('#resume-json').set_input_files({'name':'synthetic.json','mimeType':'application/json','buffer':json.dumps({'schema':'evidence-timeline-v1','records':rows}).encode()})
 page.locator('#resume-json-status').get_by_text('10000 records imported',exact=False).wait_for(timeout=30000)
 assert page.locator('#records li').count()==N
 preview=page.locator('#groups').inner_text()
 assert '5000 related-record groups' in preview and '4992 additional groups not shown' in preview
 assert len(preview)<2500, ('bounded group summary',len(preview))
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 page.locator('#review-filter').select_option('disputed')
 assert page.locator('#records li').count()==2500
 with page.expect_download() as d:page.locator('#json').click()
 export=json.loads(Path(d.value.path()).read_text())['records']
 assert len(export)==N
 assert {r['sourceId'] for r in export}=={r['sourceId'] for r in rows}
 page.evaluate("document.documentElement.style.fontSize='32px'")
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 b.close()
print('PASS: 8 synthetic 10k-record Chromium DOM import/filter/JSON export/reflow/bounded-group checks')
