'use strict';
// Real browser-local upload/download acceptance; synthetic cells only.
const assert=require('node:assert/strict');
const {createServer}=require('node:http');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {chromium,firefox,webkit}=require('playwright');
const {parseDelimited}=require('../rescue-core.js');
const root=join(__dirname,'..');
const allowed=new Map([['/','index.html'],['/index.html','index.html'],
  ['/rescue-core.js','rescue-core.js'],['/file-reader.js','file-reader.js'],
  ['/reconcile-core.js','reconcile-core.js'],['/reconcile-ui.js','reconcile-ui.js']]);
const server=createServer((req,res)=>{
 const name=allowed.get(new URL(req.url,'http://localhost').pathname);
 if(!name){res.writeHead(404).end('Not found');return;}
 try{res.writeHead(200,{'Content-Type':name.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8',
   'Cache-Control':'no-store'});res.end(readFileSync(join(root,name)));}
 catch{res.writeHead(500).end('Unavailable');}
});
const source=Buffer.from('ID,Note\r\n0001,"line one\r\nline two"\r\n0002,"lone\rreturn"\r\n0003,"line\nfeed"\r\n0004,"café \r\n 漢字"\r\n','utf8');
const expected=[['0001','line one\r\nline two'],['0002','lone\rreturn'],['0003','line\nfeed'],['0004','café \r\n 漢字']];
let checks=0;
function eq(a,b,m){assert.deepEqual(a,b,m);checks++;}
function ok(a,m){assert.ok(a,m);checks++;}
async function run(label,browserType,url){
 const browser=await browserType.launch({headless:true});
 try{
  const page=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:800}});
  const errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(url)&&!r.url().startsWith('blob:'+url))external.push(r.url());});
  const response=await page.goto(url,{waitUntil:'networkidle'});
  eq(response.status(),200,label+' served page');
  // First-file errors must be announced, keyboard discoverable, and recoverable.
  await page.locator('#file').setInputFiles({name:'synthetic-wrong-extension.txt',mimeType:'text/plain',buffer:Buffer.from('ID\\n1\\n')});
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('Choose a .csv or .tsv file'));
  eq(await page.locator('#status').getAttribute('role'),'alert',label+' invalid extension is an alert');
  eq(await page.locator('#status').getAttribute('aria-live'),'assertive',label+' invalid extension has assertive feedback');
  eq(await page.locator('#file').getAttribute('aria-invalid'),'true',label+' invalid extension identifies input');
  ok(await page.locator('#status').evaluate(el=>document.activeElement===el),label+' invalid extension focuses error');
  ok(await page.locator('#save').isDisabled(),label+' invalid extension cannot export');
  await page.locator('#file').setInputFiles({name:'synthetic-malformed.csv',mimeType:'text/csv',buffer:Buffer.from([0x49,0x44,0x0a,0xc3,0x28])});
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('Unable to open file'));
  eq(await page.locator('#status').getAttribute('role'),'alert',label+' malformed UTF-8 is an alert');
  eq(await page.locator('#file').getAttribute('aria-invalid'),'true',label+' malformed UTF-8 identifies input');
  ok(await page.locator('#status').evaluate(el=>document.activeElement===el),label+' malformed UTF-8 focuses error');
  // Keyboard activation must restore normal status and clear invalid state.
  await page.locator('#sample').focus();await page.keyboard.press('Enter');
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('synthetic example'));
  eq(await page.locator('#status').getAttribute('role'),'status',label+' valid sample restores status role');
  eq(await page.locator('#status').getAttribute('aria-live'),'polite',label+' valid sample restores polite feedback');
  eq(await page.locator('#file').getAttribute('aria-invalid'),null,label+' valid sample clears invalid state');
  await page.locator('#reset').focus();await page.keyboard.press('Enter');
  eq(await page.locator('#status').innerText(),'No data loaded.',label+' keyboard clear resets source');
  ok(await page.locator('#save').isDisabled(),label+' keyboard clear disables export');
  await page.setViewportSize({width:320,height:800});
  ok(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),label+' upload error recovery fits 320px viewport');
  await page.setViewportSize({width:1280,height:800});
  await page.locator('#file').setInputFiles({name:'synthetic-mixed-newlines.csv',mimeType:'text/csv',buffer:source});
  await page.waitForFunction(()=>document.querySelector('#saveJson')?.disabled===false);
  const [jsonDownload]=await Promise.all([page.waitForEvent('download'),page.locator('#saveJson').click()]);
  const evidence=JSON.parse(readFileSync(await jsonDownload.path(),'utf8'));
  eq(evidence.records.map(r=>r.values),expected,label+' JSON retains CRLF CR LF exact');
  eq(evidence.records.map(r=>r.sourceRecord),[2,3,4,5],label+' logical source positions');
  eq(evidence.source.fileName,'synthetic-mixed-newlines.csv',label+' source name');
  await page.locator('#sheetSafe').uncheck();
  const [csvDownload]=await Promise.all([page.waitForEvent('download'),page.locator('#save').click()]);
  eq(parseDelimited(readFileSync(await csvDownload.path(),'utf8')).rows,expected,label+' machine CSV exact round-trip');
  await page.locator('#sheetSafe').check();
  const [sheetDownload]=await Promise.all([page.waitForEvent('download'),page.locator('#save').click()]);
  const spreadsheet=readFileSync(await sheetDownload.path(),'utf8');
  ok(spreadsheet.startsWith('\uFEFF'),label+' spreadsheet BOM');
  eq(parseDelimited(spreadsheet).rows,expected,label+' spreadsheet CSV exact when no formula-like cells');
  await page.setViewportSize({width:320,height:800});
  ok(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),label+' mobile-width reflow');
  eq(errors,[],label+' no page errors');
  eq(external,[],label+' no external requests');
  // Read-only issue filters must show original logical source records, even
  // when a separate export-only deduplication option is enabled.
  const issuePage=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:800}});
  const issueErrors=[],issueExternal=[];
  issuePage.on('pageerror',error=>issueErrors.push(error.message));
  issuePage.on('request',request=>{
    if(!request.url().startsWith(url)&&!request.url().startsWith('blob:'+url))
      issueExternal.push(request.url());
  });
  eq((await issuePage.goto(url,{waitUntil:'networkidle'})).status(),200,label+' separate issue review served');
  await issuePage.locator('#file').setInputFiles({name:'synthetic-issue-review.csv',mimeType:'text/csv',
    buffer:Buffer.from('ID,Note\\n01,ok\\n02," "\\n03,ok\\n03,ok\\n04,done\\n'.replaceAll('\\n','\n'),'utf8')});
  await issuePage.waitForFunction(()=>document.querySelector('#previewFilter')?.disabled===false);
  eq(await issuePage.locator('#previewFilter').getAttribute('id'),'previewFilter',label+' source filter available');
  ok((await issuePage.locator('#previewStatus').innerText()).includes('5 source records'),
    label+' all original source records counted');
  await issuePage.locator('#previewFilter').selectOption('missing');
  eq(await issuePage.locator('#table tbody tr').count(),1,label+' one missing-cell record');
  eq(await issuePage.locator('#table tbody tr th').first().innerText(),'3',label+' missing record original position');
  eq(await issuePage.locator('#previewStatus').getAttribute('role'),'status',label+' filter count announced politely');
  await issuePage.locator('#previewFilter').selectOption('duplicates');
  eq(await issuePage.locator('#table tbody tr').count(),1,label+' one duplicate record');
  eq(await issuePage.locator('#table tbody tr th').first().innerText(),'5',label+' duplicate source position');
  eq(await issuePage.locator('#table tbody tr td').first().innerText(),'4',label+' duplicate cites first source position');
  await issuePage.locator('#dedupe').check();
  eq(await issuePage.locator('#table tbody tr th').first().innerText(),'5',
    label+' export-only deduplication cannot hide source duplicate');
  const [dedupCsv]=await Promise.all([issuePage.waitForEvent('download'),issuePage.locator('#save').click()]);
  eq(parseDelimited(readFileSync(await dedupCsv.path(),'utf8')).rows.length,4,
    label+' separate CSV export excludes one exact duplicate');
  const [issueJson]=await Promise.all([issuePage.waitForEvent('download'),issuePage.locator('#saveJson').click()]);
  eq(JSON.parse(readFileSync(await issueJson.path(),'utf8')).records.map(r=>r.sourceRecord),
    [2,3,4,5,6],label+' JSON evidence preserves all original positions');
  await issuePage.setViewportSize({width:320,height:800});
  ok(await issuePage.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),
    label+' issue filters reflow at 320px viewport');
  await issuePage.setViewportSize({width:1280,height:800});
  eq(issueErrors,[],label+' no errors during issue-filter workflow');
  eq(issueExternal,[],label+' no external requests during issue-filter workflow');
  // A 47-record synthetic input must remain inspectable beyond the first 20.
  const pageRows=Array.from({length:47},(_,i)=>
    String(i+1).padStart(3,'0')+',value-'+i).join('\\n').replaceAll('\\n','\n');
  await issuePage.locator('#file').setInputFiles({name:'synthetic-pages.csv',mimeType:'text/csv',
    buffer:Buffer.from('ID,Note\n'+pageRows+'\n','utf8')});
  await issuePage.waitForFunction(()=>document.querySelector('#previewStatus')?.textContent?.includes('47 source records'));
  ok(await issuePage.locator('#previewPrev').isDisabled(),label+' first page has no previous');
  ok(await issuePage.locator('#previewNext').isEnabled(),label+' first page has next');
  await issuePage.locator('#previewNext').focus();await issuePage.keyboard.press('Enter');
  eq(await issuePage.locator('#table tbody tr th').first().innerText(),'22',label+' keyboard next retains source record 22');
  ok((await issuePage.locator('#previewStatus').innerText()).includes('21–40 of 47'),label+' second-page range announced');
  await issuePage.locator('#previewNext').click();
  eq(await issuePage.locator('#table tbody tr').count(),7,label+' last page contains seven records');
  eq(await issuePage.locator('#table tbody tr th').first().innerText(),'42',label+' last page original position');
  ok(await issuePage.locator('#previewNext').isDisabled(),label+' last page next disabled');
  await issuePage.locator('#previewPrev').click();
  eq(await issuePage.locator('#table tbody tr th').first().innerText(),'22',label+' previous returns to original position');
  await issuePage.locator('#previewFilter').selectOption('missing');
  ok(await issuePage.locator('#previewPrev').isDisabled(),label+' filter resets page');
  ok(await issuePage.locator('#previewNext').isDisabled(),label+' empty filter disables next');
  await issuePage.locator('#reset').click();
  ok(await issuePage.locator('#previewPrev').isDisabled(),label+' clear disables previous');
  ok(await issuePage.locator('#previewNext').isDisabled(),label+' clear disables next');
  await issuePage.close();

  // Direct source-record navigation: test the actual browser interaction, not
  // only the pure lookup helper. A separate page isolates download-heavy flows.
  const jumpPage=await browser.newPage({viewport:{width:1280,height:800}});
  const jumpErrors=[],jumpExternal=[];
  jumpPage.on('pageerror',error=>jumpErrors.push(error.message));
  jumpPage.on('request',request=>{
    if(!request.url().startsWith(url)&&!request.url().startsWith('blob:'+url))
      jumpExternal.push(request.url());
  });
  eq((await jumpPage.goto(url,{waitUntil:'networkidle'})).status(),200,
    label+' direct-jump page served');
  const jumpRows=Array.from({length:50},(_,i)=>
    i===0?'01,alpha':i===1?'02,':i===49?'01,alpha':
      String(i+1).padStart(2,'0')+',value-'+i).join('\n');
  await jumpPage.locator('#file').setInputFiles({name:'synthetic-direct-jump.csv',
    mimeType:'text/csv',buffer:Buffer.from('ID,Note\n'+jumpRows+'\n','utf8')});
  await jumpPage.waitForFunction(()=>document.querySelector('#previewStatus')?.textContent?.includes('50 source records'));
  ok(await jumpPage.locator('#previewJump').isEnabled(),label+' jump input enabled on load');
  await jumpPage.locator('#previewJump').fill('51');
  await jumpPage.locator('#previewJump').focus();
  await jumpPage.keyboard.press('Enter');
  ok((await jumpPage.locator('#previewStatus').innerText()).includes('41–50 of 50'),
    label+' keyboard Enter jumps to last page');
  eq(await jumpPage.locator('#table tbody tr th').first().innerText(),'42',
    label+' direct jump shows original first source position');
  eq(await jumpPage.locator('#table tbody tr th').last().innerText(),'51',
    label+' direct jump shows target original source position');
  eq(await jumpPage.locator('#previewJump').getAttribute('aria-invalid'),null,
    label+' valid keyboard jump has no invalid state');
  ok((await jumpPage.locator('#jumpStatus').innerText()).includes('Source record 51'),
    label+' jump result is announced in text');
  eq(await jumpPage.locator('#table .jump-target').count(),1,label+' exactly one source row highlighted');
  const targetHeader=jumpPage.locator('#table .jump-target th[scope="row"]');
  eq(await targetHeader.innerText(),'51',label+' target retains exact source number');
  eq(await targetHeader.getAttribute('aria-label'),'Source record 51, jump target',label+' accessible target name');
  eq(await targetHeader.getAttribute('tabindex'),'-1',label+' target has no additional Tab stop');
  ok(await targetHeader.evaluate(el=>document.activeElement===el),label+' keyboard jump focuses source row');
  eq(await targetHeader.evaluate(el=>getComputedStyle(el).outlineStyle),'solid',label+' focused row has solid outline');
  ok(await targetHeader.evaluate(el=>getComputedStyle(el,'::after').content.includes('Jump target')),label+' target text is visible beyond color');
  ok((await jumpPage.locator('#jumpStatus').innerText()).includes('highlighted and focused'),label+' status explains focus');
  // The issue index is value-free, complete beyond the visible 20-row page,
  // and preserves original source positions and first duplicate occurrence.
  ok(await jumpPage.locator('#saveIssues').isEnabled(),label+' issue index available after upload');
  const [issueDownload]=await Promise.all([jumpPage.waitForEvent('download'),jumpPage.locator('#saveIssues').click()]);
  const issueIndex=JSON.parse(readFileSync(await issueDownload.path(),'utf8'));
  eq(issueIndex.format,'data-rescue-issue-index',label+' issue index format');
  eq(issueIndex.recordCount,50,label+' issue index covers all source records');
  eq(issueIndex.counts,{recordsWithBlankCells:1,repeatedExactRecords:1,issueRecords:2},label+' issue index counts');
  eq(issueIndex.issues,[
    {sourceRecord:3,blankColumns:[2],duplicateOf:null},
    {sourceRecord:51,blankColumns:[],duplicateOf:2}
  ],label+' issue index exact source positions');
  ok(!JSON.stringify(issueIndex).includes('alpha'),label+' issue index excludes source cell values');
  ok(!JSON.stringify(issueIndex).includes('value-'),label+' issue index excludes other cell values');
  ok(!Object.hasOwn(issueIndex,'records'),label+' issue index does not include full record array');
  ok(!await jumpPage.locator('#issueIncludeSource').isChecked(),label+' sensitive metadata unchecked by default');
  ok(!Object.hasOwn(issueIndex.source,'fileName'),label+' default index omits filename');
  ok(!Object.hasOwn(issueIndex.source,'sha256'),label+' default index omits SHA-256');
  ok(!Object.hasOwn(issueIndex.source,'byteCount'),label+' default index omits original byte count');
  await jumpPage.locator('#issueIncludeSource').focus();
  await jumpPage.keyboard.press('Space');
  ok(await jumpPage.locator('#issueIncludeSource').isChecked(),label+' keyboard opts into source metadata');
  const [identifiedDownload]=await Promise.all([jumpPage.waitForEvent('download'),jumpPage.locator('#saveIssues').click()]);
  const identifiedIndex=JSON.parse(readFileSync(await identifiedDownload.path(),'utf8'));
  eq(identifiedIndex.source.fileName,'synthetic-direct-jump.csv',label+' opt-in index identifies source filename');
  ok(/^[0-9a-f]{64}$/.test(identifiedIndex.source.sha256),label+' opt-in index includes original-byte digest');
  eq(identifiedIndex.issues,issueIndex.issues,label+' opt-in leaves exact issue positions unchanged');
  ok((await jumpPage.locator('#status').innerText()).includes('fingerprint included'),label+' opt-in status is explicit');
  
  const [jumpJson]=await Promise.all([jumpPage.waitForEvent('download'),jumpPage.locator('#saveJson').click()]);
  const jumpEvidence=JSON.parse(readFileSync(await jumpJson.path(),'utf8'));
  eq(jumpEvidence.records.length,50,label+' jump does not truncate JSON evidence');
  eq(jumpEvidence.records[49].sourceRecord,51,label+' jump preserves last source identifier');
  await jumpPage.locator('#previewPrev').click();
  eq(await jumpPage.locator('#table .jump-target').count(),0,label+' paging clears old marker');
  eq(await jumpPage.locator('#jumpStatus').innerText(),'',label+' paging clears old announcement');
  await jumpPage.locator('#previewFilter').selectOption('duplicates');
  ok((await jumpPage.locator('#previewStatus').innerText()).includes('1 repeated exact records'),
    label+' duplicate filter recalculates count');
  await jumpPage.locator('#previewJump').fill('51');
  await jumpPage.locator('#previewGo').focus();
  await jumpPage.keyboard.press('Enter');
  eq(await jumpPage.locator('#table tbody tr th').first().innerText(),'51',
    label+' keyboard button jump respects duplicate filter');
  eq(await jumpPage.locator('#table tbody tr td').first().innerText(),'2',
    label+' duplicate target cites original first occurrence');
  eq(await jumpPage.locator('#table .jump-target th[scope="row"]').getAttribute('aria-label'),'Source record 51, jump target',label+' filtered duplicate target marked');
  await jumpPage.locator('#previewFilter').selectOption('missing');
  await jumpPage.locator('#previewJump').fill('51');
  await jumpPage.locator('#previewGo').click();
  eq(await jumpPage.locator('#table .jump-target').count(),0,label+' invalid jump has no stale marker');
  eq(await jumpPage.locator('#previewJump').getAttribute('aria-invalid'),'true',
    label+' filtered-out target identifies input error');
  eq(await jumpPage.locator('#jumpStatus').getAttribute('role'),'alert',
    label+' filtered-out target is announced as alert');
  ok((await jumpPage.locator('#jumpStatus').innerText()).includes('not included in this filter'),
    label+' filtered-out target has actionable text');
  ok(await jumpPage.locator('#previewJump').evaluate(el=>document.activeElement===el),
    label+' filtered-out target restores focus');
  await jumpPage.locator('#previewJump').fill('3');
  await jumpPage.locator('#previewJump').press('Enter');
  eq(await jumpPage.locator('#table tbody tr th').first().innerText(),'3',
    label+' missing-cell source record can be reached by Enter');
  eq(await jumpPage.locator('#previewJump').getAttribute('aria-invalid'),null,
    label+' valid recovery clears invalid state');
  await jumpPage.locator('#previewJump').fill('1');
  await jumpPage.locator('#previewGo').click();
  ok((await jumpPage.locator('#jumpStatus').innerText()).includes('whole-number source record'),
    label+' header record cannot be selected as a data row');
  await jumpPage.locator('#previewFilter').selectOption('all');
  eq(await jumpPage.locator('#previewJump').getAttribute('aria-invalid'),null,
    label+' changing filter clears jump error');
  // Lexical validation must not silently accept exponent/decimal notation as a record ID.
  eq(await jumpPage.locator('#previewJump').getAttribute('type'),'text',
    label+' source-record ID is text rather than a number spinner');
  eq(await jumpPage.locator('#previewJump').getAttribute('aria-describedby'),'jumpHelp jumpStatus',
    label+' field exposes instructions and dynamic error through accessible description');
  for (const bad of ['2e0','2.0','+2','٥']) {
    await jumpPage.locator('#previewJump').fill(bad);
    await jumpPage.locator('#previewJump').press('Enter');
    eq(await jumpPage.locator('#previewJump').getAttribute('aria-invalid'),'true',
      label+' rejects non-digit source-record syntax '+bad);
    ok((await jumpPage.locator('#jumpStatus').innerText()).includes('Enter digits only'),
      label+' explains invalid source-record syntax '+bad);
    ok(await jumpPage.locator('#previewJump').evaluate(el=>document.activeElement===el),
      label+' focuses invalid source-record input '+bad);
  }
  await jumpPage.locator('#previewJump').fill('0003');
  await jumpPage.locator('#previewJump').press('Enter');
  eq(await jumpPage.locator('#previewJump').getAttribute('aria-invalid'),null,
    label+' leading-zero digits are accepted as record 3');
  ok((await jumpPage.locator('#jumpStatus').innerText()).includes('Source record 3'),
    label+' leading-zero target resolves to exact source position');
  eq(await jumpPage.locator('#table .jump-target th[scope="row"]').getAttribute('aria-label'),'Source record 3, jump target',label+' canonical leading-zero target');
  await jumpPage.setViewportSize({width:320,height:800});
  ok(await jumpPage.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),
    label+' direct-jump controls fit 320px viewport');
  await jumpPage.locator('#reset').click();
  ok(!await jumpPage.locator('#issueIncludeSource').isChecked(),label+' clear resets sensitive-metadata consent');
  ok(await jumpPage.locator('#issueIncludeSource').isDisabled(),label+' clear disables metadata option');
  eq(await jumpPage.locator('#table .jump-target').count(),0,label+' clear removes target');
  ok(await jumpPage.locator('#previewJump').isDisabled(),label+' clearing file disables jump input');
  ok(await jumpPage.locator('#previewGo').isDisabled(),label+' clearing file disables jump button');
  eq(jumpErrors,[],label+' no direct-jump page errors');
  eq(jumpExternal,[],label+' no external requests during direct jump');
  await jumpPage.close();

  // Synthetic adversarial multiline cell: spreadsheet-view export must fail closed.
  await page.locator('#file').setInputFiles({name:'synthetic-guard.csv',mimeType:'text/csv',
    buffer:Buffer.from('ID,Note\r\n01,"safe\n=1+1"\r\n','utf8')});
  await page.waitForFunction(()=>document.querySelector('#saveJson')?.disabled===false);
  await page.locator('#sheetSafe').check();
  let blockedDownload=false;
  const onDownload=()=>{blockedDownload=true;};
  page.on('download',onDownload);
  await page.locator('#save').click();
  ok((await page.locator('#status').innerText()).includes('Spreadsheet CSV blocked at source record 2, column 2'),label+' actionable export error');
  ok(await page.locator('#status').evaluate(el=>document.activeElement===el),label+' error receives focus');
  ok(!blockedDownload,label+' blocked export creates no download');
  page.off('download',onDownload);
  const [safeJson]=await Promise.all([page.waitForEvent('download'),page.locator('#saveJson').click()]);
  eq(JSON.parse(readFileSync(await safeJson.path(),'utf8')).records[0].values[1],'safe\n=1+1',label+' JSON preserves multiline source');

  // Duplicate removal must not change the logical record cited in a blocked export.
  await page.locator('#file').setInputFiles({name:'synthetic-deduped-guard.csv',mimeType:'text/csv',
    buffer:Buffer.from('ID,Note\n01,ok\n01,ok\n02,"safe\n=1+1"\n03,done\n','utf8')});
  await page.waitForFunction(()=>document.querySelector('#saveJson')?.disabled===false);
  await page.locator('#dedupe').check();
  await page.locator('#sheetSafe').check();
  await page.locator('#save').click();
  ok((await page.locator('#status').innerText()).includes('source record 4, column 2'),label+' deduplicated export cites original source position');
  const [originalEvidence]=await Promise.all([page.waitForEvent('download'),page.locator('#saveJson').click()]);
  eq(JSON.parse(readFileSync(await originalEvidence.path(),'utf8')).records.map(r=>r.sourceRecord),
    [2,3,4,5],label+' JSON still exports all original records');
  // The first-file table and completeness view must not render enormous or
  // invisible cell/header text, while evidence retains exact input bytes.
  const firstPreviewValue='start\u200B'+'Z'.repeat(210)+'\nend';
  const firstPreviewHeader='Note\u200B'+'H'.repeat(160);
  const firstPreviewCsv='ID,'+firstPreviewHeader+'\n1,"'+firstPreviewValue+'"\n';
  await page.locator('#file').setInputFiles({name:'synthetic-bounded-preview.csv',mimeType:'text/csv',
    buffer:Buffer.from(firstPreviewCsv,'utf8')});
  await page.waitForFunction(()=>document.querySelector('#saveJson')?.disabled===false);
  const previewCell=await page.locator('#table tbody tr').first().locator('td').nth(2).innerText();
  ok(previewCell.includes('\\u{200B}') && previewCell.includes('\\n'),label+' first-file cell reveals hidden characters');
  ok(previewCell.includes('code points omitted') && !previewCell.includes('Z'.repeat(100)),
    label+' first-file cell preview bounded');
  const previewHeading=await page.locator('#table thead th').nth(3).innerText();
  ok(previewHeading.includes('\\u{200B}') && previewHeading.includes('code points omitted'),
    label+' first-file header preview bounded and escaped');
  const qualityHeading=await page.locator('#columns tbody tr').nth(1).locator('th[scope="row"]').innerText();
  ok(qualityHeading.includes('\\u{200B}') && qualityHeading.includes('code points omitted'),
    label+' completeness column heading bounded and escaped');
  const [previewJson]=await Promise.all([page.waitForEvent('download'),page.locator('#saveJson').click()]);
  const exactPreviewEvidence=JSON.parse(readFileSync(await previewJson.path(),'utf8'));
  eq(exactPreviewEvidence.headers[1],firstPreviewHeader,label+' exact original header in evidence');
  eq(exactPreviewEvidence.records[0].values[1],firstPreviewValue,label+' exact original cell in evidence');
  await page.locator('#sheetSafe').uncheck();
  const [previewCsv]=await Promise.all([page.waitForEvent('download'),page.locator('#save').click()]);
  eq(parseDelimited(readFileSync(await previewCsv.path(),'utf8')).rows[0][1],firstPreviewValue,
    label+' machine CSV retains exact cell despite bounded preview');

  // Generated duplicate-header labels must never shadow literal source headers.
  // The third column must be selectable as a distinct exact-reconciliation key.
  await page.locator('#file').setInputFiles({name:'synthetic-colliding-headers.csv',mimeType:'text/csv',
    buffer:Buffer.from('ID,ID,ID (2)\\nX,A,ALPHA\\nY,B,BETA\\n'.replaceAll('\\n','\n'),'utf8')});
  await page.waitForFunction(()=>document.querySelector('#leftKey')?.options.length===4);
  eq(await page.locator('#leftKey option').allTextContents(),
    ['Select a column','ID','ID (2)','ID (2) (2)'],label+' distinct column choices');
  await page.locator('#compareFile').setInputFiles({name:'synthetic-target.csv',mimeType:'text/csv',
    buffer:Buffer.from('Join\nALPHA\nBETA\n','utf8')});
  await page.waitForFunction(()=>document.querySelector('#rightKey')?.options.length===2);
  await page.locator('#leftKey').selectOption('ID (2) (2)');
  await page.locator('#rightKey').selectOption('Join');
  await page.locator('#compareRun').click();
  ok((await page.locator('#compareStatus').innerText()).includes('2 exact one-to-one matches'),
    label+' third source column produces two exact matches');
  const [headerEvidence]=await Promise.all([page.waitForEvent('download'),page.locator('#saveJson').click()]);
  eq(JSON.parse(readFileSync(await headerEvidence.path(),'utf8')).headers,
    ['ID','ID','ID (2)'],label+' original colliding headers preserved in evidence');

  // Comparison keys may contain multiline formula-like text. CSV must fail
  // closed with an accessible recovery path; JSON must retain the exact key.
  await page.locator('#file').setInputFiles({name:'synthetic-audit-left.csv',mimeType:'text/csv',
    buffer:Buffer.from('ID,Note\\n"safe\\n=1+1",not-exported\\n'.replaceAll('\\n','\n'),'utf8')});
  await page.waitForFunction(()=>document.querySelector('#leftKey')?.options.length===3);
  await page.locator('#compareFile').setInputFiles({name:'synthetic-audit-right.csv',mimeType:'text/csv',
    buffer:Buffer.from('Join\\n"safe\\n=1+1"\\n'.replaceAll('\\n','\n'),'utf8')});
  await page.waitForFunction(()=>document.querySelector('#compareStatus')?.textContent?.includes('Loaded second file'));
  await page.locator('#leftKey').selectOption('ID');
  await page.locator('#rightKey').selectOption('Join');
  await page.locator('#compareRun').click();
  ok(await page.locator('#compareJson').isEnabled(),label+' exact audit JSON enabled after comparison');
  let auditCsvDownloaded=false;
  const onAuditCsvDownload=()=>{auditCsvDownloaded=true;};
  page.on('download',onAuditCsvDownload);
  await page.locator('#compareExport').click();
  ok((await page.locator('#compareStatus').innerText()).includes('Comparison CSV blocked at audit record 2, column 2'),
    label+' unsafe comparison CSV blocked with exact audit location');
  eq(await page.locator('#compareStatus').getAttribute('role'),'alert',label+' audit error announced as alert');
  ok(await page.locator('#compareStatus').evaluate(el=>document.activeElement===el),label+' audit error focused');
  ok(!auditCsvDownloaded,label+' unsafe comparison CSV produces no download');
  page.off('download',onAuditCsvDownload);
  ok(await page.locator('#compareJson').isEnabled(),label+' exact JSON recovery remains enabled after blocked audit CSV');
  const [auditJsonDownload]=await Promise.all([page.waitForEvent('download'),page.locator('#compareJson').click()]);
  const audit=JSON.parse(readFileSync(await auditJsonDownload.path(),'utf8'));
  eq(audit.format,'data-rescue-comparison-audit',label+' exact audit schema');
  eq(audit.source.firstKey,'ID',label+' selected source key recorded');
  eq(audit.matches,[{key:'safe\n=1+1',leftRow:2,rightRow:2}],label+' exact multiline key and logical positions');
  ok(!JSON.stringify(audit).includes('not-exported'),label+' audit omits non-key source cells');
  ok((await page.locator('#compareStatus').innerText()).includes('Exported exact comparison audit JSON'),
    label+' JSON recovery is confirmed');
  eq(await page.locator('#compareStatus').getAttribute('role'),'status',label+' success restores status role');
  eq(errors,[],label+' no page errors after audit recovery');
  eq(external,[],label+' no external requests after audit recovery');
  await page.close();
 }finally{await browser.close();}
}
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port+'/';
 try{
  for(const [name,type] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]])await run(name,type,url);
  console.log('PASS: '+checks+' real-browser exact quoted newline, JSON evidence, CSV download, privacy and reflow assertions.');
 }finally{await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
