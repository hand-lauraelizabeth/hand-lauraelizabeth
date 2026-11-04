'use strict';
const assert=require('node:assert/strict');
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright');
const source=fs.readFileSync(path.join(__dirname,'kwic-context-exercise.html'),'utf8');
const server=http.createServer((req,res)=>{res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Content-Security-Policy':"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"});res.end(source);});
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const external=[];page.on('request',r=>{if(!r.url().startsWith('http://127.0.0.1:'))external.push(r.url());});
 let checks=0;function check(actual,expected){assert.deepEqual(actual,expected);checks++;}
 const root=page.locator('#leh-kwic-lesson');
 try{
  await page.goto('http://127.0.0.1:'+server.address().port,{waitUntil:'load'});
  check(await root.getAttribute('data-ready'),'1');
  check(await root.locator('mark').count(),3);
  check((await page.locator('#leh-kwic-matches').innerText()).includes('3 occurrences in 3 of 3'),true);
  await page.getByRole('button',{name:'Check interpretation',exact:true}).click();
  check(await page.locator('#leh-kwic-feedback').innerText(),'Choose one answer before checking.');
  check(await page.evaluate(()=>document.activeElement.id),'leh-kwic-feedback');
  for(const value of ['a','b','c']){
   await root.locator('input[value="'+value+'"]').check();
   await page.getByRole('button',{name:'Check interpretation',exact:true}).click();
   const feedback=await page.locator('#leh-kwic-feedback').innerText();
   check(feedback.startsWith(value==='b'?'Correct.':'Not yet.'),true);
   check(feedback.includes('SYN-02'),true);
  }
  await page.getByLabel('Search term',{exact:true}).selectOption('work');
  check(await root.locator('mark').count(),1);
  check((await page.locator('#leh-kwic-matches').innerText()).includes('1 occurrence in 1 of 3'),true);
  check(await root.locator('input:checked').count(),0);
  await root.locator('input[value="b"]').check();
  await page.getByRole('button',{name:'Check interpretation',exact:true}).click();
  check((await page.locator('#leh-kwic-feedback').innerText()).includes('Only SYN-03'),true);
  check((await page.locator('#leh-kwic-feedback').innerText()).includes('SYN-02'),false);
  await page.getByRole('button',{name:'Download reflection (.txt)',exact:true}).click();
  check(await page.evaluate(()=>document.activeElement.id),'leh-kwic-reflection');
  check((await page.locator('#leh-kwic-download-status').innerText()).includes('Write a reflection'),true);
  const reflection='SYN-03: “although” contrasts descriptions. <script>window.bad=1</script> A count alone cannot prove agreement.';
  await page.getByLabel('Your interpretation (up to 4,000 characters)',{exact:true}).fill(reflection);
  const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Download reflection (.txt)',exact:true}).click()]);
  check(download.suggestedFilename(),'context-before-count-reflection.txt');
  const output=fs.readFileSync(await download.path(),'utf8');
  check(output.includes(reflection),true);check(output.includes('SYN-01:'),true);check(output.includes('Search term at download: work'),true);
  check(await page.evaluate(()=>typeof window.bad),'undefined');
  check(await root.locator('a[download]').count(),0);
  await page.getByRole('button',{name:'Reset exercise',exact:true}).click();
  check(await page.getByLabel('Your interpretation (up to 4,000 characters)',{exact:true}).inputValue(),'');
  check(await page.evaluate(()=>document.activeElement.id),'leh-kwic-term');
  await page.getByLabel('Search term',{exact:true}).press('Tab');
  check(await page.evaluate(()=>document.activeElement.id),'leh-kwic-show');
  await page.locator('#leh-kwic-show').press('Enter');check(await root.locator('mark').count(),3);
  await page.setViewportSize({width:320,height:900});
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
  check(await root.locator('.kwic-rubric article').count(),4);
  check(external,[]);check(errors,[]);
  await page.screenshot({path:path.join(process.env.RUNNER_TEMP||__dirname,'kwic-mobile.png'),fullPage:true});
  console.log('PASS: '+checks+' browser assertions; both terms, all answer paths, keyboard, reflection download, reset, 320px reflow, no external requests or page errors.');
 } finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
