'use strict';
// Browser-local acceptance tests use generated, non-sensitive CSV fixtures only.
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
let checks=0;
function eq(a,b,message){assert.deepEqual(a,b,message);checks++;}
function ok(a,message){assert.ok(a,message);checks++;}
const LIMIT=5000000, ROWS=50000;
const regular=Array.from({length:ROWS-1},(_,i)=>String(i+1).padStart(7,'0')+','+'x'.repeat(88)+'\n').join('');
const prefix='ID,Payload\n'+regular+'0050000,'+'x'.repeat(88);
const exact=Buffer.from(prefix+'x'.repeat(LIMIT-Buffer.byteLength(prefix)),'utf8');
eq(exact.byteLength,LIMIT,'synthetic fixture is exactly 5,000,000 UTF-8 bytes');
const oracle=createHash('sha256').update(exact).digest('hex');
const overflowRows=Buffer.from('ID\n'+Array.from({length:ROWS+1},(_,i)=>String(i+1)).join('\n'),'utf8');
ok(overflowRows.byteLength<LIMIT,'50,001-row fixture remains below byte limit');
async function run(name,engine,url){
 const browser=await engine.launch({headless:true});
 try{
  const page=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:800}});
  page.setDefaultTimeout(90000);
  const errors=[],outside=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(url)&&!r.url().startsWith('blob:'+url))outside.push(r.url());});
  await page.addInitScript(()=>{
   window.__ft01Lag={maxMs:0,ticks:0};
   let last=performance.now();
   setInterval(()=>{const now=performance.now();window.__ft01Lag.maxMs=Math.max(window.__ft01Lag.maxMs,now-last-100);window.__ft01Lag.ticks++;last=now;},100);
  });
  const response=await page.goto(url,{waitUntil:'networkidle'});
  eq(response.status(),200,name+' HTTP-served page');
  const start=Date.now();
  await page.locator('#file').setInputFiles({name:'max.csv',mimeType:'text/csv',buffer:exact});
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('Loaded max.csv'),null,{timeout:90000});
  const loadMs=Date.now()-start;
  ok(await page.locator('#saveJson').isEnabled(),name+' exact 5 MB accepted');
  eq((await page.locator('#metrics .metric strong').first().innerText()).trim(),'50000',name+' full 50,000 rows visible in summary');
  const lag=await page.evaluate(()=>window.__ft01Lag);
  ok(lag.maxMs<15000,name+' no browser-main-thread stall over 15 seconds at limit');
  ok(loadMs<60000,name+' 5 MB load completed within 60 seconds');
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#saveJson').click()]);
  const evidence=JSON.parse(readFileSync(await download.path(),'utf8'));
  eq(evidence.recordCount,ROWS,name+' JSON retains all 50,000 source records');
  eq(evidence.records.length,ROWS,name+' JSON array complete');
  eq(evidence.records[0].sourceRecord,2,name+' first logical source record');
  eq(evidence.records[ROWS-1].sourceRecord,ROWS+1,name+' final logical source record');
  eq(evidence.records[ROWS-1].values[0],'0050000',name+' final source identifier');
  eq(evidence.source.byteCount,LIMIT,name+' original byte count preserved');
  eq(evidence.source.sha256,oracle,name+' independent SHA-256 oracle at 5 MB');
  await page.setViewportSize({width:320,height:800});
  ok(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth<=1),name+' 320px reflow with maximum file');
  await page.locator('#file').setInputFiles({name:'over.csv',mimeType:'text/csv',buffer:Buffer.alloc(LIMIT+1,0x61)});
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('larger than 5 MB'));
  ok(await page.locator('#saveJson').isDisabled(),name+' oversized file cannot export stale evidence');
  await page.locator('#file').setInputFiles({name:'too-many.csv',mimeType:'text/csv',buffer:overflowRows});
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('More than 50,000 data rows'));
  ok(await page.locator('#saveJson').isDisabled(),name+' excessive row count fails closed');
  await page.locator('#file').setInputFiles({name:'recovery.csv',mimeType:'text/csv',buffer:Buffer.from('ID,Note\n0001,safe\n')});
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('Loaded recovery.csv'));
  ok(await page.locator('#saveJson').isEnabled(),name+' valid import recovers after two failures');
  eq(errors,[],name+' no unhandled browser exceptions');
  eq(outside,[],name+' no off-origin requests');
  console.log(name+': exact 5MB/50k load '+loadMs+'ms, longest timer delay '+Math.round(lag.maxMs)+'ms; export hash, limit failures, recovery PASS');
  await page.close();
 }finally{await browser.close();}
}
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port+'/';
 try{
  for(const [name,engine] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]])await run(name,engine,url);
  console.log('PASS: '+checks+' exact-byte/row boundary and recovery assertions across three engines.');
  console.log('Native screen-reader, physical mobile, native browser zoom and spreadsheet-app reopening remain unverified.');
 }finally{await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
