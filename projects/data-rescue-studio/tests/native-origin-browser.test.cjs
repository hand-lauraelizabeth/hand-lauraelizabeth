'use strict';
// FT-01 acceptance: exercise real browser security contexts, not mocked SubtleCrypto.
// All page assets and uploads are synthetic; no network responses are fetched.
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {createHash}=require('node:crypto');
const {chromium,firefox,webkit}=require('playwright');
const root=join(__dirname,'..');
const assets=new Map([
 ['/', 'index.html'],['/index.html','index.html'],
 ['/rescue-core.js','rescue-core.js'],['/file-reader.js','file-reader.js'],
 ['/reconcile-core.js','reconcile-core.js'],['/provenance-core.js','provenance-core.js'],['/reconcile-evidence.js','reconcile-evidence.js'],['/reconcile-ui.js','reconcile-ui.js']
]);
const fixture=Buffer.from('ID,Note\r\n0007,"=1+2"\r\n0008,"café"\r\n','utf8');
const expectedHash=createHash('sha256').update(fixture).digest('hex');
let assertions=0;
function equal(actual,expected,message){assert.deepEqual(actual,expected,message);assertions++;}
function yes(value,message){assert.ok(value,message);assertions++;}
async function run(engineName,engine,origin,secure){
 const browser=await engine.launch({headless:true});
 try{
  const page=await browser.newPage({acceptDownloads:true,viewport:{width:375,height:812}});
  const errors=[],unexpected=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',request=>{
   if(!request.url().startsWith(origin+'/'))unexpected.push(request.url());
  });
  await page.route('**/*',async route=>{
   const requestUrl=new URL(route.request().url());
   const path=assets.get(requestUrl.pathname);
   if(requestUrl.origin!==origin||!path){
    unexpected.push(route.request().url());
    await route.abort('blockedbyclient');
    return;
   }
   await route.fulfill({
    status:200,
    contentType:path.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8',
    headers:{'Cache-Control':'no-store'},
    body:readFileSync(join(root,path))
   });
  });
  const response=await page.goto(origin+'/',{waitUntil:'load',timeout:30000});
  equal(response.status(),200,engineName+' '+origin+' synthetic page served');
  const environment=await page.evaluate(()=>({
   secure:globalThis.isSecureContext,
   subtle:typeof globalThis.crypto?.subtle,
   origin:globalThis.location.origin
  }));
  equal(environment.secure,secure,engineName+' native secure-context flag');
  equal(environment.subtle,secure?'object':'undefined',engineName+' native WebCrypto exposure');
  equal(environment.origin,origin,engineName+' origin preserved without navigation');
  const name=secure?'trustworthy.csv':'insecure.csv';
  await page.locator('#file').setInputFiles({name,mimeType:'text/csv',buffer:fixture});
  await page.waitForFunction(n=>document.querySelector('#status')?.textContent?.includes('Loaded '+n),name);
  const status=await page.locator('#status').innerText();
  yes(status.includes(secure?'SHA-256 is available':'SHA-256 is unavailable'),engineName+' accurate status before export');
  const [download]=await Promise.all([
   page.waitForEvent('download'),
   page.locator('#saveJson').click()
  ]);
  const evidence=JSON.parse(readFileSync(await download.path(),'utf8'));
  equal(evidence.source.fileName,name,engineName+' original filename retained');
  equal(evidence.records.map(record=>record.sourceRecord),[2,3],engineName+' logical record positions retained');
  equal(evidence.records[0].values,['0007','=1+2'],engineName+' formula-like value and identifier retained');
  equal(evidence.records[1].values,['0008','café'],engineName+' Unicode retained');
  if(secure){
   equal(evidence.source.sha256,expectedHash,engineName+' genuine original-byte digest');
   equal(evidence.source.byteCount,fixture.byteLength,engineName+' original-byte length');
  }else{
   yes(!Object.hasOwn(evidence.source,'sha256'),engineName+' no fabricated SHA-256');
   yes(!Object.hasOwn(evidence.source,'digestAlgorithm'),engineName+' no fabricated algorithm');
   yes(!Object.hasOwn(evidence.source,'byteCount'),engineName+' no unverified source byte count');
   yes((await page.locator('#status').innerText()).includes('No original-byte fingerprint available'),engineName+' export status discloses absence');
  }
  yes(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth<=1),engineName+' mobile-width reflow');
  await page.locator('#reset').click();
  yes(await page.locator('#saveJson').isDisabled(),engineName+' clear disables stale export');
  equal(errors,[],engineName+' no unhandled page errors');
  equal(unexpected,[],engineName+' no unexpected external requests');
  await page.close();
  console.log(engineName+' '+(secure?'trustworthy loopback':'native insecure non-loopback')+': PASS');
 }finally{await browser.close();}
}
(async()=>{
 for(const [name,engine] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]]){
  await run(name,engine,'http://127.0.0.1:45671',true);
  await run(name,engine,'http://ft01-untrusted.invalid',false);
 }
 console.log('PASS: '+assertions+' native secure/insecure-origin browser assertions.');
 console.log('Browser routes served synthetic assets locally. No real remote server, native AT, physical mobile, or spreadsheet reopen/resave tested.');
})().catch(error=>{console.error(error);process.exitCode=1;});
