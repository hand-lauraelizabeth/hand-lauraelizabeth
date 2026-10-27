'use strict';
// Synthetic-only keyboard and error-recovery checks; no user files or external services.
const assert=require('node:assert/strict');
const {createServer}=require('node:http');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {chromium,firefox,webkit}=require('playwright');
const root=join(__dirname,'..');
const files=new Map([['/','index.html'],['/index.html','index.html'],['/rescue-core.js','rescue-core.js'],['/file-reader.js','file-reader.js'],['/reconcile-core.js','reconcile-core.js'],['/reconcile-ui.js','reconcile-ui.js']]);
const server=createServer((req,res)=>{
 const file=files.get(new URL(req.url,'http://localhost').pathname);
 if(!file){res.writeHead(404).end('Not found');return;}
 res.writeHead(200,{'Content-Type':file.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8','Cache-Control':'no-store'});
 res.end(readFileSync(join(root,file)));
});
let checks=0;
function eq(actual,expected,label){assert.deepEqual(actual,expected,label);checks++;}
function ok(value,label){assert.ok(value,label);checks++;}
async function checkBrowser(label,type,url){
 const browser=await type.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:800},acceptDownloads:true});
  const errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(url)&&!r.url().startsWith('blob:'+url))external.push(r.url());});
  eq((await page.goto(url,{waitUntil:'networkidle'})).status(),200,label+' local page');
  eq(await page.locator('#file').getAttribute('aria-describedby'),'status',label+' upload references feedback');
  await page.locator('#file').setInputFiles({name:'bad.txt',mimeType:'text/plain',buffer:Buffer.from('ID\n1')});
  eq(await page.locator('#status').getAttribute('role'),'alert',label+' unsupported format announced');
  eq(await page.locator('#file').getAttribute('aria-invalid'),'true',label+' invalid file exposed');
  eq(await page.evaluate(()=>document.activeElement.id),'status',label+' error receives focus');
  ok((await page.locator('#status').innerText()).includes('.csv or .tsv'),label+' actionable extension error');
  ok(!(await page.locator('#saveJson').isEnabled()),label+' stale export unavailable after error');
  await page.locator('#sample').focus();
  await page.keyboard.press('Enter');
  ok((await page.locator('#status').innerText()).includes('synthetic example'),label+' sample keyboard activation');
  eq(await page.locator('#status').getAttribute('role'),'status',label+' success is non-error status');
  eq(await page.locator('#file').getAttribute('aria-invalid'),'false',label+' invalid flag clears on success');
  await page.locator('#reset').focus();
  await page.keyboard.press('Enter');
  ok(!(await page.locator('#save').isEnabled()),label+' reset keyboard activation');
  await page.locator('#file').setInputFiles({name:'broken.csv',mimeType:'text/csv',buffer:Buffer.from([0xc3,0x28])});
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Unable to open file'));
  eq(await page.evaluate(()=>document.activeElement.id),'status',label+' invalid UTF-8 error focused');
  eq(await page.locator('#status').getAttribute('role'),'alert',label+' decoding error announced');
  eq(await page.locator('#file').getAttribute('aria-invalid'),'true',label+' decoding error marks input invalid');
  await page.locator('#file').setInputFiles({name:'valid.csv',mimeType:'text/csv',buffer:Buffer.from('ID,Note\n0001,café\n','utf8')});
  await page.waitForFunction(()=>document.querySelector('#saveJson').disabled===false);
  eq(await page.locator('#file').getAttribute('aria-invalid'),'false',label+' valid retry clears invalid flag');
  eq(await page.locator('#status').getAttribute('role'),'status',label+' valid retry clears alert');
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#saveJson').click()]);
  const data=JSON.parse(readFileSync(await download.path(),'utf8'));
  eq(data.records[0].values,['0001','café'],label+' recovered exact data');
  // The second-file upload must provide the same actionable error and recovery path.
  const second=page.locator('#compareFile');
  eq(await second.getAttribute('aria-describedby'),'compareStatus',label+' second upload references feedback');
  await second.setInputFiles({name:'notes.txt',mimeType:'text/plain',buffer:Buffer.from('ID\\n0001')});
  eq(await page.locator('#compareStatus').getAttribute('role'),'alert',label+' second format error announced');
  eq(await second.getAttribute('aria-invalid'),'true',label+' second format error marks file');
  eq(await page.evaluate(()=>document.activeElement.id),'compareStatus',label+' second format error focused');
  ok((await page.locator('#compareStatus').innerText()).includes('.csv or .tsv'),label+' second format error actionable');
  ok(!(await page.locator('#compareRun').isEnabled()),label+' comparison disabled after second-file error');
  await second.setInputFiles({name:'too-large.csv',mimeType:'text/csv',buffer:Buffer.alloc(5000001,65)});
  eq(await page.locator('#compareStatus').getAttribute('role'),'alert',label+' second size error announced');
  eq(await second.getAttribute('aria-invalid'),'true',label+' second size error marks file');
  eq(await page.evaluate(()=>document.activeElement.id),'compareStatus',label+' second size error focused');
  await second.setInputFiles({name:'invalid.csv',mimeType:'text/csv',buffer:Buffer.from([0xc3,0x28])});
  await page.waitForFunction(()=>document.querySelector('#compareStatus').textContent.includes('Unable to read second file'));
  eq(await page.locator('#compareStatus').getAttribute('role'),'alert',label+' second UTF-8 error announced');
  eq(await second.getAttribute('aria-invalid'),'true',label+' second UTF-8 error marks file');
  eq(await page.evaluate(()=>document.activeElement.id),'compareStatus',label+' second UTF-8 error focused');
  await second.setInputFiles({name:'second.csv',mimeType:'text/csv',buffer:Buffer.from('ID,Note\\n0001,other\\n','utf8')});
  await page.waitForFunction(()=>document.querySelector('#compareStatus').textContent.includes('Loaded second file'));
  eq(await page.locator('#compareStatus').getAttribute('role'),'status',label+' valid second upload clears alert');
  eq(await second.getAttribute('aria-invalid'),'false',label+' valid second upload clears invalid flag');
  await page.locator('#leftKey').selectOption('ID');
  await page.locator('#rightKey').selectOption('ID');
  ok(await page.locator('#compareRun').isEnabled(),label+' comparison restored after second-file retry');
  await page.locator('#compareRun').click();
  ok((await page.locator('#compareStatus').innerText()).includes('1 exact one-to-one matches'),label+' exact match after retry');
  await page.locator('#compareClear').focus();
  await page.keyboard.press('Enter');
  eq(await second.getAttribute('aria-invalid'),'false',label+' keyboard clear resets second invalid state');
  ok(!(await page.locator('#compareRun').isEnabled()),label+' keyboard clear disables stale comparison');
  eq(await page.locator('#compareStatus').getAttribute('role'),'status',label+' keyboard clear restores status role');
  await page.setViewportSize({width:320,height:800});
  ok(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),label+' 320px reflow');
  eq(errors,[],label+' no page exceptions');
  eq(external,[],label+' no off-origin requests');
  await page.close();
 }finally{await browser.close();}
}
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port+'/';
 try{
  for(const [name,browser] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]])await checkBrowser(name,browser,url);
  console.log('PASS: '+checks+' cross-browser synthetic upload-error focus, keyboard, recovery, export, privacy and 320px reflow assertions.');
 }finally{await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
