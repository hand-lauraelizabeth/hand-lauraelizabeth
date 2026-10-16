'use strict';
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch();
 let checks=0;
 const check=(condition,label)=>{assert.ok(condition,label);checks++;};
 try{
  for(const html of ['index.html','history-preview.html']){
   const page=await browser.newPage({viewport:{width:320,height:800}});
   const status=html==='index.html'?'#status':'#loadStatus';
   const errors=[],requests=[];
   page.on('pageerror',error=>errors.push(error.message));
   page.on('request',request=>{if(/^https?:/i.test(request.url()))requests.push(request.url());});
   await page.goto(pathToFileURL(path.resolve(__dirname,'..',html)).href);
   const upload=(name,buffer)=>page.locator('#file').setInputFiles({name,mimeType:'text/csv',buffer:Buffer.isBuffer(buffer)?buffer:Buffer.from(buffer)});
   check(await page.locator('#file').getAttribute('aria-describedby')===status.slice(1),html+': input describes error status');
   check(await page.locator('#file').getAttribute('aria-invalid')==='false',html+': initial validity');
   check(await page.locator(status).getAttribute('tabindex')==='-1',html+': error programmatically focusable');
   await upload('invalid.exe','ID,Value\n1,test');
   await page.waitForFunction(selector=>document.querySelector(selector).textContent.includes('.csv or .tsv'),status);
   check(await page.locator('#file').getAttribute('aria-invalid')==='true',html+': extension error invalid');
   check(await page.evaluate(selector=>document.activeElement===document.querySelector(selector),status),html+': extension error focused');
   check(await page.locator('#save').isDisabled(),html+': invalid upload cannot export');
   await upload('oversize.csv',Buffer.alloc(5000001,0x20));
   await page.waitForFunction(selector=>document.querySelector(selector).textContent.includes('5 MB'),status);
   check(await page.evaluate(selector=>document.activeElement===document.querySelector(selector),status),html+': size error focused');
   await upload('valid.csv','ID,Value\n1,Ada');
   await page.waitForFunction(selector=>document.querySelector(selector).textContent.includes('Loaded'),status);
   check(await page.locator('#file').getAttribute('aria-invalid')==='false',html+': valid upload clears invalid state');
   check(await page.locator('#save').isEnabled(),html+': valid upload enables export');
   check(!await page.evaluate(selector=>document.activeElement===document.querySelector(selector),status),html+': successful upload does not steal focus');
   await upload('invalid.csv',Buffer.from([0x49,0x44,0x0a,0xc3,0x28]));
   await page.waitForFunction(selector=>document.querySelector(selector).textContent.includes('Invalid UTF-8'),status);
   check(await page.locator('#file').getAttribute('aria-invalid')==='true',html+': reader error invalid');
   check(await page.evaluate(selector=>document.activeElement===document.querySelector(selector),status),html+': reader error focused');
   await page.locator('#reset').click();
   check(await page.locator('#file').getAttribute('aria-invalid')==='false',html+': reset clears invalid');
   check(await page.locator('#save').isDisabled(),html+': reset disables export');
   check((await page.locator('#file').inputValue())==='',html+': reset clears file reference');
   check((await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth))<=1,html+': 320px reflow');
   check(errors.length===0,html+': no uncaught errors');
   check(requests.length===0,html+': no remote requests');
   await page.close();
  }
  console.log('PASS: '+checks+' Chromium primary upload focus, recovery, privacy and 320px reflow checks.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
