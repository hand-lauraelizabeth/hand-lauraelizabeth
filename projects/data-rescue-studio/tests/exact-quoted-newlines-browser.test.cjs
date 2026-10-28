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
