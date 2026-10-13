'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch();
 let passed=0;
 const ok=(value,label)=>{assert.ok(value,label);passed++;};
 try {
  for(const width of [1280,320]){
   const page=await browser.newPage({viewport:{width,height:800},acceptDownloads:true});
   const failures=[];page.on('pageerror',e=>failures.push(e.message));
   await page.goto(pathToFileURL(path.resolve(__dirname,'../index.html')).href);
   await page.locator('#file').setInputFiles({name:'one.csv',mimeType:'text/csv',buffer:Buffer.from('ID,Name\n1,Ada\n2,Ben\n2,Ben Again')});
   await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('3 data rows'));
   await page.locator('#compareFile').setInputFiles({name:'two.csv',mimeType:'text/csv',buffer:Buffer.from('Code,Value\n1,10\n2,20\n3,30')});
   await page.waitForFunction(()=>document.querySelector('#compareStatus').textContent.includes('Loaded second file'));
   await page.locator('#leftKey').selectOption('ID');
   await page.locator('#rightKey').selectOption('Code');
   await page.locator('#compareRun').click();
   await page.waitForFunction(()=>document.querySelector('#compareStatus').textContent.includes('Comparison complete'));
   ok((await page.locator('#compareMetrics .metric strong').allInnerTexts()).join(',')==='1,1,0,1,0','classifications correct');
   const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#compareExport').click()]);
   const csv=fs.readFileSync(await download.path(),'utf8');
   ok(csv.includes('Ambiguous')&&csv.includes('Second file only'),'CSV contains evidence records');
   ok(failures.length===0,'no uncaught JavaScript errors');
   if(width===320){
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
    ok(overflow<=1,'320px width has no horizontal overflow');
    await page.setViewportSize({width:640,height:800});
    await page.evaluate(()=>{document.documentElement.style.zoom='2'});
    const zoomOverflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
    ok(zoomOverflow<=1,'200 percent CSS zoom has no horizontal overflow');
    await page.locator('#compareRun').focus();
    await page.keyboard.press('Enter');
    ok(await page.locator('#compareExport').isEnabled(),'keyboard comparison works');
   }
   await page.close();
  }
  console.log('PASS: '+passed+' Chromium upload, audit, keyboard, mobile and zoom checks.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
