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
const expected=parseDelimited(source.toString('utf8')).rows;
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
