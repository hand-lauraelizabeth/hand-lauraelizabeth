'use strict';
// HTTP-served synthetic-only JSON download and accessible recovery acceptance.
const assert=require('node:assert/strict');
const {createServer}=require('node:http');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {chromium,firefox,webkit}=require('playwright');
const root=join(__dirname,'..');
const assets=new Map([['/','index.html'],['/index.html','index.html'],
 ['/rescue-core.js','rescue-core.js'],['/file-reader.js','file-reader.js'],
 ['/reconcile-core.js','reconcile-core.js'],['/comparison-issue-index.js','comparison-issue-index.js'],
 ['/reconcile-ui.js','reconcile-ui.js']]);
const server=createServer((req,res)=>{
 const path=assets.get(new URL(req.url,'http://localhost').pathname);
 if(!path){res.writeHead(404).end('Not found');return;}
 try{res.writeHead(200,{'Content-Type':path.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8','Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'none'; object-src 'none'"});res.end(readFileSync(join(root,path)));}
 catch{res.writeHead(500).end('Unavailable');}
});
let checks=0;
function eq(a,b,msg){assert.deepStrictEqual(a,b,msg);checks++;}
function ok(v,msg){assert.ok(v,msg);checks++;}
const input=Buffer.from('ID,Value\n0007,=2+2\n0007,=2+2\n0008,\n','utf8');
async function run(name,engine,url){
 const browser=await engine.launch({headless:true});
 try{
  const page=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:800}});
  const errors=[],outside=[];let downloads=0;
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(url)&&!r.url().startsWith('blob:'+url))outside.push(r.url());});
  page.on('download',()=>downloads++);
  eq((await page.goto(url,{waitUntil:'networkidle'})).status(),200,name+' HTTP served');
  await page.locator('#file').setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:input});
  await page.waitForFunction(()=>document.querySelector('#saveJson')?.disabled===false);
  const [issue]=await Promise.all([page.waitForEvent('download'),page.locator('#saveIssues').click()]);
  const index=JSON.parse(readFileSync(await issue.path(),'utf8'));
  eq(index.issues,[{sourceRecord:3,blankColumns:[],duplicateOf:2},
   {sourceRecord:4,blankColumns:[2],duplicateOf:null}],name+' exact index findings');
  ok(!Object.hasOwn(index.source,'fileName'),name+' filename omitted by default');
  ok(!JSON.stringify(index).includes('0007'),name+' values excluded');
  await page.evaluate(()=>{
   window.__evidenceExport=window.DataRescue.exportEvidenceJson;
   window.DataRescue.exportEvidenceJson=()=>{throw Error('Evidence JSON exceeds the 32 MB output limit.');};
  });
  const before=downloads;
  await page.locator('#saveJson').click();
  ok((await page.locator('#status').innerText()).includes('32 MB output limit'),name+' readable size error');
  eq(await page.locator('#status').getAttribute('role'),'alert',name+' error alert');
  ok(await page.locator('#status').evaluate(el=>el===document.activeElement),name+' error focus');
  eq(await page.locator('#file').getAttribute('aria-invalid'),null,name+' valid file not marked invalid by export error');
  ok(await page.locator('#saveJson').isEnabled(),name+' source preserved for retry');
  await page.waitForTimeout(100);
  eq(downloads,before,name+' oversized export starts no download');
  await page.evaluate(()=>{window.DataRescue.exportEvidenceJson=window.__evidenceExport;});
  const [evidence]=await Promise.all([page.waitForEvent('download'),page.locator('#saveJson').click()]);
  const full=JSON.parse(readFileSync(await evidence.path(),'utf8'));
  eq(full.records.map(r=>r.sourceRecord),[2,3,4],name+' exact JSON retry');
  eq(full.records[0].values,['0007','=2+2'],name+' formula-like input preserved in JSON');
  await page.evaluate(()=>{
   window.__issueExport=window.DataRescue.exportIssueIndexJson;
   window.DataRescue.exportIssueIndexJson=()=>{throw Error('SECRET_INTERNAL_IDENTIFIER');};
  });
  await page.locator('#saveIssues').click();
  const message=await page.locator('#status').innerText();
  ok(message.includes('Could not prepare issue index JSON'),name+' generic preparation recovery');
  ok(!message.includes('SECRET_INTERNAL_IDENTIFIER'),name+' internal exception not disclosed');
  ok(await page.locator('#status').evaluate(el=>el===document.activeElement),name+' issue error focused');
  await page.evaluate(()=>{window.DataRescue.exportIssueIndexJson=window.__issueExport;});
  await page.evaluate(()=>{
   window.__createObjectURL=URL.createObjectURL;
   URL.createObjectURL=()=>{throw Error('SECRET_OBJECT_URL');};
  });
  await page.locator('#saveJson').click();
  const blocked=await page.locator('#status').innerText();
  ok(blocked.includes('JSON download could not be started'),name+' blocked download recovery');
  ok(!blocked.includes('SECRET_OBJECT_URL'),name+' object URL exception hidden');
  await page.evaluate(()=>{URL.createObjectURL=window.__createObjectURL;});
  await page.evaluate(()=>{
   window.__anchorClick=HTMLAnchorElement.prototype.click;
   window.__revokeObjectURL=URL.revokeObjectURL;
   window.__revoked=0;
   URL.revokeObjectURL=function(value){window.__revoked++;return window.__revokeObjectURL.call(URL,value);};
   HTMLAnchorElement.prototype.click=function(){throw Error('SECRET_CLICK');};
  });
  await page.locator('#saveIssues').click();
  ok((await page.locator('#status').innerText()).includes('JSON download could not be started'),name+' blocked anchor activation recovery');
  ok(await page.evaluate(()=>window.__revoked>=1),name+' failed URL revoked');
  eq(await page.evaluate(()=>document.querySelectorAll('a[download]').length),0,name+' temporary anchor removed');
  await page.evaluate(()=>{
   HTMLAnchorElement.prototype.click=window.__anchorClick;
   URL.revokeObjectURL=window.__revokeObjectURL;
  });
  const [recovered]=await Promise.all([page.waitForEvent('download'),page.locator('#saveIssues').click()]);
  eq(JSON.parse(readFileSync(await recovered.path(),'utf8')).counts.issueRecords,2,name+' issue download recovers');
  await page.setViewportSize({width:320,height:800});
  ok(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth<=1),name+' 320px reflow');
  eq(errors,[],name+' no uncaught errors');
  eq(outside,[],name+' no off-origin requests');
  await page.close();
  console.log(name+': JSON boundary, privacy, focus, URL cleanup and retry PASS');
 }finally{await browser.close();}
}
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port+'/';
 try{
  for(const [name,engine] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]])await run(name,engine,url);
  console.log('FT-01 JSON HTTP/CSP browser assertions: '+checks+'/'+checks+' PASS');
 }finally{await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
