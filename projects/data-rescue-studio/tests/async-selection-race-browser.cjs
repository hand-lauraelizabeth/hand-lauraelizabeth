'use strict';
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch();
 let assertions=0;
 const check=(value,label)=>{assert.ok(value,label);assertions++;};
 try{
  for(const html of ['index.html','history-preview.html']){
   const page=await browser.newPage({viewport:{width:320,height:820}});
   const errors=[],requests=[];
   page.on('pageerror',e=>errors.push(e.message));
   page.on('request',r=>{if(/^https?:/i.test(r.url()))requests.push(r.url())});
   await page.goto(pathToFileURL(path.resolve(__dirname,'..',html)).href);
   await page.evaluate(()=>{
    const original=window.DataRescueFileReader.read;
    window.__pendingReads=[];
    window.DataRescueFileReader.read=(file,parser)=>new Promise((resolve,reject)=>{
     window.__pendingReads.push({name:file.name,complete:()=>Promise.resolve().then(()=>original(file,parser)).then(resolve,reject)});
    });
   });
   const choose=(selector,name,text)=>page.locator(selector).setInputFiles({name,mimeType:'text/csv',buffer:Buffer.from(text)});
   const complete=index=>page.evaluate(async i=>{await window.__pendingReads[i].complete()},index);
   const status=html==='index.html'?'#status':'#loadStatus';
   await choose('#file','old.csv','ID,Value\nold,stale');
   await choose('#file','new.csv','ID,Value\nnew,fresh');
   await complete(1);
   await page.waitForFunction(([s])=>document.querySelector(s).textContent.includes('new.csv'),[status]);
   await complete(0);
   check((await page.locator(status).innerText()).includes('new.csv'),html+': stale first file does not replace newer file');
   check(!(await page.locator(status).innerText()).includes('old.csv'),html+': stale file status suppressed');
   await choose('#file','clear-late.csv','ID,Value\nlate,stale');
   await page.locator('#reset').click();
   await complete(2);
   check((await page.locator(status).innerText()).includes(html==='index.html'?'No data loaded.':'No file loaded.'),html+': reset invalidates pending primary read');
   check(await page.locator('#save').isDisabled(),html+': stale primary read cannot reenable export');
   await choose('#file','sample-late.csv','ID,Value\nlate,stale');
   await page.locator('#sample').click();
   await complete(3);
   check(!(await page.locator(status).innerText()).includes('sample-late.csv'),html+': synthetic example supersedes pending primary read');
   await choose('#compareFile','second-old.csv','ID,Value\nold,stale');
   await choose('#compareFile','second-new.csv','ID,Value\nnew,fresh');
   await complete(5);
   await page.waitForFunction(()=>document.querySelector('#compareStatus').textContent.includes('Loaded second file'));
   await complete(4);
   check((await page.locator('#compareStatus').innerText()).includes('1 rows'),html+': second file newer read remains loaded');
   check(await page.locator('#rightKey').isEnabled(),html+': newest second file keys remain selectable');
   await choose('#compareFile','second-clear.csv','ID,Value\nlate,stale');
   await page.locator('#compareClear').click();
   await complete(6);
   check(await page.locator('#rightKey').isDisabled(),html+': second-file clear invalidates pending read');
   check(await page.locator('#compareRun').isDisabled(),html+': cleared second file cannot reconcile');
   check(errors.length===0,html+': no uncaught browser errors');
   check(requests.length===0,html+': no remote requests');
   await page.close();
  }
  console.log('PASS: '+assertions+' async file-selection race and privacy checks in Chromium.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
