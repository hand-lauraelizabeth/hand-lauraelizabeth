'use strict';
// Actual browser downloads; synthetic inputs only; no Excel/Sheets application is invoked.
const assert=require('node:assert/strict');
const {createServer}=require('node:http');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {chromium,firefox,webkit}=require('playwright');
const {parseDelimited}=require('../rescue-core.js');
const root=join(__dirname,'..');
const allow=new Map([['/','index.html'],['/index.html','index.html'],['/rescue-core.js','rescue-core.js'],['/file-reader.js','file-reader.js'],['/reconcile-core.js','reconcile-core.js'],['/comparison-issue-index.js','comparison-issue-index.js'],['/reconcile-ui.js','reconcile-ui.js']]);
const server=createServer((req,res)=>{
 const path=allow.get(new URL(req.url,'http://localhost').pathname);
 if(!path){res.writeHead(404).end('Not found');return;}
 try{res.writeHead(200,{'Content-Type':path.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8','Cache-Control':'no-store'});res.end(readFileSync(join(root,path)));}
 catch{res.writeHead(500).end('Unavailable');}
});
let checks=0;
function eq(a,b,m){assert.deepEqual(a,b,m);checks++;}
function ok(a,m){assert.ok(a,m);checks++;}
const left=Buffer.from('ID,Value,Note\r\n0007,=1+2,café\r\n0007,=1+2,café\r\n=x,+SUM(1),漢字\r\n','utf8');
const right=Buffer.from('ID,Label\r\n0007,ok\r\n=x,ok\r\n','utf8');
async function run(name,type,url){
 const browser=await type.launch({headless:true});
 try{
  const page=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:800}});
  const errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(url)&&!r.url().startsWith('blob:'+url))external.push(r.url());});
  const response=await page.goto(url,{waitUntil:'networkidle'});
  eq(response.status(),200,name+' HTTP served');
  await page.locator('#file').setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:left});
  await page.waitForFunction(()=>document.querySelector('#save')?.disabled===false);
  ok(await page.locator('#sheetSafe').isChecked(),name+' spreadsheet precaution defaults on');
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#save').click()]);
  const bytes=readFileSync(await download.path());
  eq([...bytes.subarray(0,3)],[239,187,191],name+' downloaded UTF-8 BOM bytes');
  const safe=parseDelimited(bytes.toString('utf8'));
  eq(safe.rows[0],['0007','\t=1+2','café'],name+' spreadsheet formula precaution and Unicode');
  eq(safe.rows.length,3,name+' duplicate records retained');
  await page.locator('#sheetSafe').uncheck();
  const [rawDownload]=await Promise.all([page.waitForEvent('download'),page.locator('#save').click()]);
  const raw=readFileSync(await rawDownload.path());
  ok(!raw.subarray(0,3).equals(Buffer.from([239,187,191])),name+' machine export has no BOM');
  eq(parseDelimited(raw.toString('utf8')).rows[0],['0007','=1+2','café'],name+' machine export exact values');
  await page.locator('#compareFile').setInputFiles({name:'second.csv',mimeType:'text/csv',buffer:right});
  await page.waitForFunction(()=>document.querySelector('#rightKey')?.disabled===false);
  await page.locator('#leftKey').selectOption('ID');
  await page.locator('#rightKey').selectOption('ID');
  await page.locator('#compareRun').click();
  ok(await page.locator('#compareExport').isEnabled(),name+' comparison ready');
  const [auditDownload]=await Promise.all([page.waitForEvent('download'),page.locator('#compareExport').click()]);
  const audit=readFileSync(await auditDownload.path());
  eq([...audit.subarray(0,3)],[239,187,191],name+' audit UTF-8 BOM');
  const auditRows=parseDelimited(audit.toString('utf8')).rows;
  ok(auditRows.some(row=>row[1]==='\t=x'),name+' audit identifier formula precaution');
  await page.setViewportSize({width:320,height:800});
  const overflow=await page.evaluate(()=>({
    delta:document.documentElement.scrollWidth-document.documentElement.clientWidth,
    viewport:document.documentElement.clientWidth, bodyWidth:document.body.scrollWidth, regions:['columns','table','compareMetrics','compareResults'].map(id=>{const e=document.getElementById(id);return {id,client:e.clientWidth,scroll:e.scrollWidth,rect:e.getBoundingClientRect().toJSON()};}),
    overflowing:[...document.querySelectorAll('body *')].filter(e=>{
      const box=e.getBoundingClientRect();
      return box.width && (box.right>document.documentElement.clientWidth+1 || box.left < -1);
    }).sort((a,b)=>b.getBoundingClientRect().right-a.getBoundingClientRect().right).slice(0,15).map(e=>({tag:e.tagName,id:e.id,cls:e.className,parent:e.parentElement?.id||e.parentElement?.className,rect:{
      left:Math.round(e.getBoundingClientRect().left),right:Math.round(e.getBoundingClientRect().right)
    }}))
  }));
  if(overflow.delta>1) console.error(name+' 320px overflow diagnostics: '+JSON.stringify(overflow));
  ok(overflow.delta<=1,name+' 320 CSS-pixel outer page reflow');
  eq(errors,[],name+' no page errors');
  eq(external,[],name+' no external requests');
  await page.close();
 }finally{await browser.close();}
}
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port+'/';
 try{
  for(const [name,type] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]])await run(name,type,url);
  console.log('PASS: '+checks+' real-browser UTF-8 BOM, machine CSV, reconciliation audit, privacy and reflow assertions.');
  console.log('Excel and Google Sheets native reopen/resave and native screen-reader/zoom/physical mobile remain unverified.');
 }finally{await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
