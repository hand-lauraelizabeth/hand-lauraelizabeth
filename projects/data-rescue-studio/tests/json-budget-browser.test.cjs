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
 try{res.writeHead(200,{'Content-Type':path.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8','Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'none'; object-src 'none'"});res.end(readFileSync(join(root,path)));}
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
  // The page uses an inline stylesheet. If the test CSP blocks it, native
  // file controls can overflow even though the product CSS is correct.
  eq(await page.evaluate(()=>getComputedStyle(document.body).marginLeft),'0px',name+' inline CSS active under CSP');
  eq(await page.locator('#file').evaluate(el=>getComputedStyle(el).minWidth),'0px',name+' file-input responsive CSS active');
  await page.locator('#file').setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:input});
  await page.waitForFunction(()=>document.querySelector('#saveJson')?.disabled===false);
  const [issue]=await Promise.all([page.waitForEvent('download'),page.locator('#saveIssues').click()]);
  const index=JSON.parse(readFileSync(await issue.path(),'utf8'));
  eq(index.issues,[{sourceRecord:3,blankColumns:[],duplicateOf:2},
   {sourceRecord:4,blankColumns:[2],duplicateOf:null}],name+' exact index findings');
  ok(!Object.hasOwn(index.source,'fileName'),name+' filename omitted by default');
  ok(!JSON.stringify(index).includes('0007'),name+' values excluded');
  // The parent CSV handler threw an uncaught error if blob URLs were blocked.
  await page.evaluate(()=>{
   window.__csvURL=URL.createObjectURL;
   URL.createObjectURL=()=>{throw Error('SECRET_CSV_URL');};
  });
  const csvBefore=downloads;
  await page.locator('#save').click();
  ok((await page.locator('#status').innerText()).includes('CSV download could not be started'),name+' CSV URL error');
  eq(await page.locator('#status').getAttribute('role'),'alert',name+' CSV error alert');
  ok(await page.locator('#status').evaluate(el=>el===document.activeElement),name+' CSV error focused');
  eq(await page.locator('#file').getAttribute('aria-invalid'),null,name+' CSV input remains valid');
  ok(await page.locator('#save').isEnabled(),name+' CSV retry enabled');
  ok(!(await page.locator('#status').innerText()).includes('SECRET_CSV_URL'),name+' no exception leak');
  await page.waitForTimeout(100);
  eq(downloads,csvBefore,name+' failed CSV did not download');
  await page.evaluate(()=>{
   URL.createObjectURL=window.__csvURL;
   window.__csvClick=HTMLAnchorElement.prototype.click;
   window.__csvRevoke=URL.revokeObjectURL;
   window.__csvRevoked=0;
   URL.revokeObjectURL=function(url){window.__csvRevoked++;return window.__csvRevoke.call(URL,url);};
   HTMLAnchorElement.prototype.click=function(){throw Error('SECRET_CSV_CLICK');};
  });
  await page.locator('#save').click();
  ok((await page.locator('#status').innerText()).includes('CSV download could not be started'),name+' CSV click error');
  ok(await page.evaluate(()=>window.__csvRevoked>=1),name+' failed CSV blob URL revoked');
  eq(await page.evaluate(()=>document.querySelectorAll('a[download]').length),0,name+' CSV anchor removed');
  await page.evaluate(()=>{
   HTMLAnchorElement.prototype.click=window.__csvClick;
   URL.revokeObjectURL=window.__csvRevoke;
  });
  const [csvDownload]=await Promise.all([page.waitForEvent('download'),page.locator('#save').click()]);
  const csvContent=readFileSync(await csvDownload.path(),'utf8');
  ok(csvContent.startsWith('\\uFEFF'.replace('\\uFEFF','\uFEFF')),name+' CSV BOM retained');
  ok(csvContent.includes('"\\t=2+2"'.replace('\\t','\t')),name+' formula precaution retained');
  ok((await page.locator('#status').innerText()).includes('CSV download started'),name+' CSV initiation message');
  // The comparison controller previously had an unguarded Blob URL/click
  // path for all three formats. Exercise failures and successful retries.
  await page.locator('#compareFile').setInputFiles({name:'synthetic-second.csv',mimeType:'text/csv',buffer:input});
  await page.waitForFunction(()=>[...document.querySelector('#rightKey').options].some(o=>o.value==='ID'));
  await page.locator('#leftKey').selectOption('ID');
  await page.locator('#rightKey').selectOption('ID');
  await page.locator('#compareRun').click();
  await page.waitForFunction(()=>document.querySelector('#compareIndex')?.disabled===false);
  await page.evaluate(()=>{
   window.__compareURL=URL.createObjectURL;
   URL.createObjectURL=()=>{throw Error('SECRET_COMPARISON_URL');};
  });
  for(const [selector,label] of [
   ['#compareExport','Comparison CSV'],['#compareJson','Comparison audit JSON'],
   ['#compareIndex','Reconciliation issue index']]){
   const prior=downloads;
   await page.locator(selector).click();
   const error=await page.locator('#compareStatus').innerText();
   ok(error.includes(label+' download could not be started'),name+' '+label+' URL failure');
   ok(!error.includes('SECRET_COMPARISON_URL'),name+' '+label+' no internal error disclosure');
   eq(await page.locator('#compareStatus').getAttribute('role'),'alert',name+' '+label+' alert');
   ok(await page.locator('#compareStatus').evaluate(el=>el===document.activeElement),name+' '+label+' error focus');
   eq(await page.locator('#compareFile').getAttribute('aria-invalid'),null,name+' '+label+' source remains valid');
   ok(await page.locator(selector).isEnabled(),name+' '+label+' retry available');
   eq(downloads,prior,name+' '+label+' no failed download');
  }
  await page.evaluate(()=>{
   URL.createObjectURL=window.__compareURL;
   window.__compareClick=HTMLAnchorElement.prototype.click;
   window.__compareRevoke=URL.revokeObjectURL;
   window.__compareRevoked=0;
   URL.revokeObjectURL=function(url){window.__compareRevoked++;return window.__compareRevoke.call(URL,url);};
   HTMLAnchorElement.prototype.click=function(){throw Error('SECRET_COMPARISON_CLICK');};
  });
  await page.locator('#compareJson').click();
  ok((await page.locator('#compareStatus').innerText()).includes('Comparison audit JSON download could not be started'),name+' comparison click failure');
  ok(await page.evaluate(()=>window.__compareRevoked>=1),name+' comparison failed URL revoked');
  eq(await page.evaluate(()=>document.querySelectorAll('a[download]').length),0,name+' comparison anchor removed');
  await page.evaluate(()=>{
   HTMLAnchorElement.prototype.click=window.__compareClick;
   URL.revokeObjectURL=window.__compareRevoke;
  });
  const [compareCsv]=await Promise.all([page.waitForEvent('download'),page.locator('#compareExport').click()]);
  ok(readFileSync(await compareCsv.path(),'utf8').startsWith('\uFEFF'),name+' comparison CSV retry BOM');
  ok((await page.locator('#compareStatus').innerText()).includes('download started'),name+' comparison CSV truthful status');
  // FT-03 exact comparison JSON must honor the shared 32 MB UTF-8 cap.
  // A synthetic fault checks that an over-budget export cannot start a download
  // or invalidate either uploaded source; the value-free index remains usable.
  await page.evaluate(()=>{
   window.__compareBudget=window.DataRescue.requireJsonBudget;
   window.DataRescue.requireJsonBudget=()=>{throw Error('Comparison audit JSON exceeds the 32 MB output limit.');};
  });
  const compareBefore=downloads;
  await page.locator('#compareJson').click();
  ok((await page.locator('#compareStatus').innerText()).includes('32 MB output limit'),name+' comparison JSON budget error');
  eq(await page.locator('#compareStatus').getAttribute('role'),'alert',name+' comparison JSON budget alert');
  ok(await page.locator('#compareStatus').evaluate(el=>el===document.activeElement),name+' comparison JSON budget focused');
  eq(await page.locator('#compareFile').getAttribute('aria-invalid'),null,name+' valid comparison input not invalidated by budget');
  ok(await page.locator('#compareJson').isEnabled(),name+' comparison JSON retry enabled');
  ok(await page.locator('#compareIndex').isEnabled(),name+' value-free index available after JSON budget');
  await page.waitForTimeout(100);
  eq(downloads,compareBefore,name+' over-budget comparison starts no download');
  await page.evaluate(()=>{window.DataRescue.requireJsonBudget=window.__compareBudget;});
  const [compareJson]=await Promise.all([page.waitForEvent('download'),page.locator('#compareJson').click()]);
  const comparisonAudit=JSON.parse(readFileSync(await compareJson.path(),'utf8'));
  eq(comparisonAudit.source.firstKey,'ID',name+' comparison JSON exact first key');
  eq(comparisonAudit.source.secondKey,'ID',name+' comparison JSON exact second key');
  const [compareIndex]=await Promise.all([page.waitForEvent('download'),page.locator('#compareIndex').click()]);
  const comparisonIndex=readFileSync(await compareIndex.path(),'utf8');
  ok(!comparisonIndex.includes('0007'),name+' comparison issue index excludes identifiers');
  ok((await page.locator('#compareStatus').innerText()).includes('download started'),name+' comparison index truthful status');


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
  // Wait for two layout frames after resizing, especially in WebKit.
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const geometry=await page.evaluate(()=>{
   const root=document.documentElement;
   const delta=root.scrollWidth-root.clientWidth;
   const offenders=[...document.querySelectorAll('body *')].filter(el=>{
    const rect=el.getBoundingClientRect();
    return rect.right>root.clientWidth+1 && getComputedStyle(el).overflowX!=='auto';
   }).slice(0,6).map(el=>({tag:el.tagName,id:el.id,width:Math.round(el.getBoundingClientRect().width)}));
   const pickers=[...document.querySelectorAll('input[type=file]')].map(el=>{
    const rect=el.getBoundingClientRect(),parent=el.parentElement.getBoundingClientRect();
    return {id:el.id,left:Math.round(rect.left),right:Math.round(rect.right),
      width:Math.round(rect.width),cssWidth:getComputedStyle(el).width,
      parentWidth:Math.round(parent.width),parentOverflow:getComputedStyle(el.parentElement).overflowX};
   });
   return {delta,scrollWidth:root.scrollWidth,clientWidth:root.clientWidth,offenders,pickers};
  });
  ok(geometry.delta<=1,name+' 320px reflow '+JSON.stringify(geometry));
  await page.locator('#file').setInputFiles({name:'narrow.csv',mimeType:'text/csv',buffer:input});
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('Loaded narrow.csv'));
  ok(await page.locator('#saveJson').isEnabled(),name+' primary file picker remains usable at 320px');
  await page.locator('#compareFile').setInputFiles({name:'second.csv',mimeType:'text/csv',buffer:input});
  ok(await page.locator('#compareFile').evaluate(el=>el.files?.length===1),name+' second picker remains usable at 320px');
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
