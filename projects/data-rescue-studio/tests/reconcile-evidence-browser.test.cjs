'use strict';
// Three-engine browser-local evidence download test using synthetic identifiers only.
const assert=require('node:assert/strict');
const {createServer}=require('node:http');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {chromium,firefox,webkit}=require('playwright');
const root=join(__dirname,'..');
const files=new Map([['/','index.html'],['/index.html','index.html'],['/rescue-core.js','rescue-core.js'],['/file-reader.js','file-reader.js'],['/reconcile-core.js','reconcile-core.js'],['/provenance-core.js','provenance-core.js'],['/reconcile-evidence.js','reconcile-evidence.js'],['/reconcile-ui.js','reconcile-ui.js']]);
const server=createServer((req,res)=>{
 const file=files.get(new URL(req.url,'http://localhost').pathname);
 if(!file){res.writeHead(404).end('Not found');return;}
 res.writeHead(200,{'Content-Type':file.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8','Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"});
 res.end(readFileSync(join(root,file)));
});
let checks=0;
function eq(a,b,label){assert.deepEqual(a,b,label);checks++;}
function ok(a,label){assert.ok(a,label);checks++;}
async function runEngine(label,type,url){
 const browser=await type.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:800},acceptDownloads:true});
  const errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(url)&&!r.url().startsWith('blob:'+url))external.push(r.url());});
  eq((await page.goto(url,{waitUntil:'networkidle'})).status(),200,label+' local page');
  ok(!(await page.locator('#compareExportJson').isEnabled()),label+' no premature export');
  const left='ID,Note\n0001,"line one\r\nline two"\n0001,duplicate\n=1+2,formula\ncafé,accent\n,missing\n';
  const right='Ref,Note\n0001,match\n=1+2,ok\ncafé,ok\n9999,only\n,missing\n';
  await page.locator('#file').setInputFiles({name:'first.csv',mimeType:'text/csv',buffer:Buffer.from(left,'utf8')});
  await page.waitForFunction(()=>document.querySelector('#saveJson').disabled===false);
  await page.locator('#compareFile').setInputFiles({name:'second.csv',mimeType:'text/csv',buffer:Buffer.from(right,'utf8')});
  await page.waitForFunction(()=>document.querySelector('#rightKey').disabled===false);
  await page.locator('#leftKey').selectOption('ID');
  await page.locator('#rightKey').selectOption('Ref');
  await page.locator('#compareRun').click();
  ok(await page.locator('#compareExportJson').isEnabled(),label+' comparison enables JSON');
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#compareExportJson').click()]);
  eq(download.suggestedFilename(),'data-rescue-comparison-evidence.json',label+' download name');
  const raw=readFileSync(await download.path(),'utf8'),doc=JSON.parse(raw);
  eq(doc.schema,'data-rescue-reconciliation/v1',label+' schema');
  eq(doc.sources.first.fileName,'first.csv',label+' first source');
  eq(doc.sources.second.keyColumn,'Ref',label+' second selected key');
  eq(doc.counts,{matches:2,ambiguous:1,leftOnly:0,rightOnly:1,missingLeft:1,missingRight:1},label+' all finding categories');
  eq(doc.recordCounts,{first:{total:5,matched:2,ambiguous:2,firstOnly:0,missingIdentifier:1},second:{total:5,matched:2,ambiguous:1,secondOnly:1,missingIdentifier:1}},label+' JSON row coverage');
  ok((await page.locator('#compareStatus').innerText()).includes('5 of 5'),label+' accessible completed row coverage');
  eq(await page.locator('#compareMetrics .metric').count(),9,label+' group and row metrics visible');
  eq(doc.findings.find(x=>x.identifier==='0001'),{classification:'ambiguous',identifier:'0001',firstFileRecords:[2,3],secondFileRecords:[2]},label+' ambiguous exact IDs');
  eq(doc.findings.find(x=>x.identifier==='=1+2'),{classification:'match',identifier:'=1+2',firstFileRecords:[4],secondFileRecords:[3]},label+' formula-like exact key');
  eq(doc.findings.find(x=>x.identifier==='café').firstFileRecords,[5],label+' Unicode');
  eq(doc.findings.filter(x=>x.identifier===null).length,2,label+' missing keys explicit');
  eq(raw.includes('\\t=1+2'),false,label+' no formula-prefix mutation in JSON');
  eq(raw.includes('line one'),false,label+' no full original records');
  await page.locator('#leftKey').selectOption('Note');
  ok(!(await page.locator('#compareExportJson').isEnabled()),label+' changed key invalidates stale export');
  await page.locator('#leftKey').selectOption('ID');
  await page.locator('#compareRun').click();
  ok(await page.locator('#compareExportJson').isEnabled(),label+' rerun restores export');
  await page.locator('#compareClear').click();
  ok(!(await page.locator('#compareExportJson').isEnabled()),label+' clearing second file revokes export');

  // Real HTTP-served DOM regression: direct primary replacement must revoke an
  // already-completed comparison even when the replacement has identical headers.
  await page.locator('#compareFile').setInputFiles({name:'second-again.csv',mimeType:'text/csv',buffer:Buffer.from(right,'utf8')});
  await page.waitForFunction(()=>!document.querySelector('#rightKey').disabled);
  await page.locator('#rightKey').selectOption('Ref');
  await page.locator('#compareRun').click();
  ok(await page.locator('#compareExportJson').isEnabled(),label+' completed comparison ready before replacement');
  await page.evaluate(()=>{
    window.DataRescueCompareUI.setPrimary(
      window.DataRescue.parseDelimited('ID,Note\\n9999,replacement'.replace('\\n','\n')),
      'replacement.csv'
    );
  });
  ok(!(await page.locator('#rightKey').isEnabled()),label+' primary replacement clears old second-file key');
  ok(!(await page.locator('#compareRun').isEnabled()),label+' primary replacement disables old comparison');
  ok(!(await page.locator('#compareExport').isEnabled()),label+' primary replacement revokes CSV audit');
  ok(!(await page.locator('#compareExportJson').isEnabled()),label+' primary replacement revokes JSON audit');
  eq(await page.locator('#compareFile').inputValue(),'',label+' primary replacement clears selected second file');
  eq(await page.locator('#compareResults').locator('table').count(),0,label+' primary replacement clears old findings');

  // Hold the actual File.arrayBuffer() read; replace primary while the second
  // file is pending, then release its bytes. A stale completion must be ignored.
  await page.evaluate(()=>{
    window.__slowReadStarted=false;
    window.__releaseSlow=null;
    const original=File.prototype.arrayBuffer;
    File.prototype.arrayBuffer=function(){
      if(this.name!=='slow.csv')return original.call(this);
      window.__slowReadStarted=true;
      return new Promise(resolve=>{
        window.__releaseSlow=()=>resolve(new TextEncoder().encode('Ref,Note\\n9999,stale'.replace('\\n','\n')).buffer);
      });
    };
  });
  await page.locator('#compareFile').setInputFiles({name:'slow.csv',mimeType:'text/csv',buffer:Buffer.from('Ref,Note\n9999,stale')});
  await page.waitForFunction(()=>window.__slowReadStarted===true);
  await page.evaluate(()=>{
    window.DataRescueCompareUI.setPrimary(
      window.DataRescue.parseDelimited('ID,Note\\n0007,current'.replace('\\n','\n')),
      'current.csv'
    );
    window.__releaseSlow();
  });
  await page.waitForTimeout(100);
  ok(!(await page.locator('#rightKey').isEnabled()),label+' pending stale second file cannot enable key after replacement');
  ok(!(await page.locator('#compareRun').isEnabled()),label+' pending stale second file cannot enable compare');
  ok(!(await page.locator('#compareExportJson').isEnabled()),label+' pending stale second file cannot enable export');
  ok((await page.locator('#compareStatus').innerText()).includes('First file ready'),label+' stale read cannot replace current primary status');
  eq(await page.locator('#compareFile').inputValue(),'',label+' pending stale selection stays cleared');

  await page.setViewportSize({width:320,height:800});
  ok(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),label+' 320px reflow');
  eq(errors,[],label+' no uncaught browser errors');
  eq(external,[],label+' no off-origin requests');
  await page.close();
 }finally{await browser.close();}
}
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port+'/';
 try{
  for(const [label,type] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]])await runEngine(label,type,url);
  console.log('PASS: '+checks+' synthetic cross-browser exact reconciliation JSON, provenance, stale-export and local-only assertions.');
 }finally{await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
