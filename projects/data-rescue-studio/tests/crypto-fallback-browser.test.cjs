'use strict';
// Browser acceptance: a missing/rejected digest must never become fabricated provenance.
// Only synthetic local files are used; no user data, external requests, or persistence.
const assert=require('node:assert/strict');
const {createServer}=require('node:http');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {createHash}=require('node:crypto');
const {chromium,firefox,webkit}=require('playwright');
const root=join(__dirname,'..');
const assets=new Map([['/','index.html'],['/index.html','index.html'],['/rescue-core.js','rescue-core.js'],['/file-reader.js','file-reader.js'],['/reconcile-core.js','reconcile-core.js'],['/reconcile-ui.js','reconcile-ui.js']]);
const server=createServer((req,res)=>{
 const asset=assets.get(new URL(req.url,'http://localhost').pathname);
 if(!asset){res.writeHead(404).end('Not found');return;}
 try{res.writeHead(200,{'Content-Type':asset.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8','Cache-Control':'no-store'});res.end(readFileSync(join(root,asset)));}
 catch{res.writeHead(500).end('Asset unavailable');}
});
const fixture=Buffer.from('ID,Value\r\n0009,"=SUM(1,2)"\r\n0010,café\r\n','utf8');
const expectedHash=createHash('sha256').update(fixture).digest('hex');
let checks=0;
function eq(a,b,message){assert.deepEqual(a,b,message);checks++;}
function ok(a,message){assert.ok(a,message);checks++;}
async function importCsv(page,name){
 await page.locator('#file').setInputFiles({name,mimeType:'text/csv',buffer:fixture});
 await page.waitForFunction(n=>document.querySelector('#status')?.textContent?.includes('Loaded '+n),name);
}
async function evidence(page){
 const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#saveJson').click()]);
 return JSON.parse(readFileSync(await download.path(),'utf8'));
}
async function run(name,engine,url){
 const browser=await engine.launch({headless:true});
 try{
  const page=await browser.newPage({acceptDownloads:true,viewport:{width:375,height:812}});
  const errors=[],outside=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(url)&&!r.url().startsWith('blob:'+url))outside.push(r.url());});
  const response=await page.goto(url,{waitUntil:'networkidle'});
  eq(response.status(),200,name+' HTTP-served');
  await importCsv(page,'original.csv');
  ok((await page.locator('#status').innerText()).includes('SHA-256 is available'),name+' successful digest disclosed before export');
  const original=await evidence(page);
  eq(original.source.sha256,expectedHash,name+' genuine digest matches independent Node oracle');
  eq(original.source.byteCount,fixture.byteLength,name+' genuine source byte count');
  await page.locator('#reset').click();
  // Emulates browsers without subtle crypto (including some insecure contexts);
  // does not claim to be a native insecure-context test.
  eq(await page.evaluate(()=>{
   Object.defineProperty(window.crypto,'subtle',{configurable:true,value:undefined});
   return typeof window.crypto.subtle;
  }),'undefined',name+' missing crypto injected and confirmed');
  await importCsv(page,'no-crypto.csv');
  ok((await page.locator('#status').innerText()).includes('SHA-256 is unavailable'),name+' missing digest disclosed before export');
  const absent=await evidence(page);
  eq(absent.source.fileName,'no-crypto.csv',name+' no-crypto source filename');
  eq(absent.records.map(r=>r.sourceRecord),[2,3],name+' no-crypto source IDs');
  eq(absent.records[0].values,['0009','=SUM(1,2)'],name+' no-crypto exact decoded values');
  ok(!Object.hasOwn(absent.source,'sha256'),name+' no fabricated digest');
  ok(!Object.hasOwn(absent.source,'digestAlgorithm'),name+' no fabricated algorithm');
  ok(!Object.hasOwn(absent.source,'byteCount'),name+' no unverified byte count');
  ok((await page.locator('#status').innerText()).includes('No original-byte fingerprint available'),name+' export warns absent provenance');
  // Digest promise rejection must degrade to explicit absence, not stale previous hash.
  eq(await page.evaluate(()=>{
   Object.defineProperty(window.crypto,'subtle',{configurable:true,value:{digest:async()=>{throw Error('synthetic digest rejection');}}});
   return typeof window.crypto.subtle.digest;
  }),'function',name+' digest rejection injected');
  await importCsv(page,'rejected-digest.csv');
  ok((await page.locator('#status').innerText()).includes('SHA-256 is unavailable'),name+' digest rejection disclosed');
  const rejected=await evidence(page);
  ok(!Object.hasOwn(rejected.source,'sha256'),name+' rejected digest not misreported');
  eq(rejected.source.fileName,'rejected-digest.csv',name+' no stale source filename');
  // Malformed successful digest is a hard error: never allow stale evidence download.
  await page.evaluate(()=>Object.defineProperty(window.crypto,'subtle',{configurable:true,value:{digest:async()=>new ArrayBuffer(8)}}));
  await page.locator('#file').setInputFiles({name:'bad-digest.csv',mimeType:'text/csv',buffer:fixture});
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('source-file fingerprint was invalid'));
  ok(await page.locator('#saveJson').isDisabled(),name+' invalid digest fails closed');
  ok((await page.locator('#status').getAttribute('class'))==='error',name+' invalid digest error visibly identified');
  await page.evaluate(()=>delete window.crypto.subtle);
  await importCsv(page,'recovered.csv');
  const recovered=await evidence(page);
  eq(recovered.source.sha256,expectedHash,name+' genuine digest recovered after invalid case');
  eq(recovered.source.fileName,'recovered.csv',name+' recovered source filename');
  ok(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth<=1),name+' 375px reflow');
  eq(errors,[],name+' no unhandled browser errors');
  eq(outside,[],name+' no off-origin requests');
  await page.close();
  console.log(name+': available, missing, rejected, malformed and recovered SHA-256 provenance PASS');
 }finally{await browser.close();}
}
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port+'/';
 try{
  for(const [name,engine] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]])await run(name,engine,url);
  console.log('PASS: '+checks+' cross-browser cryptography fallback and provenance assertions.');
  console.log('Native insecure-origin, screen-reader, browser zoom, physical mobile and Excel/Sheets reopen/resave remain unverified.');
 }finally{await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
