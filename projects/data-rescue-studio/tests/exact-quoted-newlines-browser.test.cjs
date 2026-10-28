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
  const previewCell=await page.locator('#table tbody tr').first().locator('td').nth(1).innerText();
  ok(previewCell.includes('\\u{200B}') && previewCell.includes('\\n'),label+' first-file cell reveals hidden characters');
  ok(previewCell.includes('code points omitted') && !previewCell.includes('Z'.repeat(100)),
    label+' first-file cell preview bounded');
  const previewHeading=await page.locator('#table thead th').nth(1).innerText();
  ok(previewHeading.includes('\\u{200B}') && previewHeading.includes('code points omitted'),
    label+' first-file header preview bounded and escaped');
  const qualityHeading=await page.locator('#columns tbody tr').nth(1).locator('td').first().innerText();
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
