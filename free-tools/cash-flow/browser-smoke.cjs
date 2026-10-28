'use strict';
const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch();let checks=0;
 const check=(ok,label)=>{assert.ok(ok,label);checks++};
 try{
  const page=await browser.newPage({viewport:{width:320,height:800},acceptDownloads:true});
  const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/i.test(r.url())&&!r.url().startsWith('http://127.0.0.1:'))requests.push(r.url())});
  const root=path.resolve(__dirname);
  const server=require('node:http').createServer((req,res)=>{
   const fs=require('node:fs'),p=req.url==='/'?'index.html':decodeURIComponent(req.url.slice(1));
   if(!['index.html','app.mjs','engine.mjs','plan.mjs','shortfalls.mjs','coverage.mjs','style.css'].includes(p)){res.writeHead(404);res.end();return}
   res.setHeader('Content-Type',p.endsWith('.mjs')?'text/javascript':p.endsWith('.css')?'text/css':'text/html');
   res.end(fs.readFileSync(path.join(root,p)));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try{
   await page.goto('http://127.0.0.1:'+server.address().port+'/');
   check(await page.locator('h1').innerText()==='Cash Flow & Bill Timing Simulator','page title');
   check(await page.locator('#export').isDisabled(),'export initially disabled');
   await page.locator('#calculate').click();
   check(await page.locator('#export').isEnabled(),'empty schedule calculates');
   check((await page.locator('#shortfall-summary').innerText()).includes('no projected below-zero end-of-day dates'),'shortfall status reports empty schedule');
   check((await page.locator('#results tr').count())>0,'daily output visible');
   await page.locator('#opening').fill('not money');await page.locator('#calculate').click();
   check(await page.locator('#export').isDisabled(),'invalid amount blocks export');
   check((await page.locator('#error').innerText()).length>0,'error is visible');
   await page.locator('#opening').fill('100.00');
   await page.locator('#event-id').fill('rent');
   await page.locator('#event-label').fill('Rent');
   await page.locator('#event-amount').fill('-50.00');
   await page.locator('#event-date').fill('2026-10-20');
   await page.locator('#event-form button[type=submit]').click();
   check((await page.locator('#events').innerText()).includes('rent'),'event added');
   await page.locator('#calculate').click();
   check((await page.locator('#summary').innerText()).includes('minimum'),'scenario summary visible');
   const downloadPromise=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadPromise;
   check(download.suggestedFilename()==='cash-flow-scenario.csv','CSV download name');
   const fs=require('node:fs');const csv=fs.readFileSync(await download.path(),'utf8');
   check(csv.includes('2026-10-20'),'CSV contains projected date');

   // Browser-level synthetic regression: do not expose unsafe CSV downloads.
   await page.locator('#event-id').fill('00009');
   await page.locator('#event-label').fill('\u200B=SUM(1,2)');
   await page.locator('#event-amount').fill('-1.00');
   await page.locator('#event-date').fill('2026-10-21');
   await page.locator('#event-form button[type=submit]').click();
   await page.locator('#calculate').click();
   check(await page.locator('#export').isDisabled(),'formula-like CSV blocked');
   check(await page.locator('#export-json').isEnabled(),'lossless JSON alternative available');
   check((await page.locator('#csv-warning').innerText()).includes('CSV export unavailable'),'visible CSV warning');
   const jsonPromise=page.waitForEvent('download');
   await page.locator('#export-json').click();
   const jsonDownload=await jsonPromise;
   check(jsonDownload.suggestedFilename()==='cash-flow-scenario.json','JSON download name');
   const json=JSON.parse(fs.readFileSync(await jsonDownload.path(),'utf8'));
   check(json.schema==='cash-flow-scenario/v1','JSON versioned schema');
   check(json.days.some(d=>d.events.some(e=>e.id==='00009'&&e.label==='\u200B=SUM(1,2)')),'exact unsafe label and leading-zero ID preserved in JSON');
   await page.evaluate(()=>{document.documentElement.style.zoom='2'});
   check((await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth))<=1,'320px layout at 200% CSS zoom');
   check(errors.length===0,'no uncaught browser errors');check(requests.length===0,'no remote requests');
  }finally{await new Promise(resolve=>server.close(resolve));await page.close()}
  console.log('PASS: '+checks+' FT-04 served Chromium workflow checks.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
