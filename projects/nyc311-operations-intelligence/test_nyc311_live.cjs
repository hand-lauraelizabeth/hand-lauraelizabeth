const {chromium}=require('playwright'); const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:800}});
  const errors=[];page.on('pageerror',e=>{errors.push(e.message);console.log('PAGE ERROR:',e.message)});page.on('console',m=>{if(m.type()==='error')console.log('CONSOLE ERROR:',m.text())});page.on('requestfailed',q=>console.log('REQUEST FAILED:',q.url(),q.failure()?.errorText));page.on('response',r=>{if(r.url().includes('erm2-nwe9'))console.log('API RESPONSE:',r.status(),r.url().slice(0,140))});
  await page.goto('https://www.lauraelizabethhand.com/nyc-311-operations-explorer-demo/',{waitUntil:'domcontentloaded',timeout:45000});
  await page.waitForTimeout(12000);console.log('LIVE DOM STATE:',JSON.stringify(await page.evaluate(()=>({status:document.querySelector('.nyc311-demo #status')?.textContent,sourceHidden:document.querySelector('.nyc311-demo #source')?.hidden,requests:document.querySelector('.nyc311-demo #requests')?.textContent,scriptCount:document.querySelectorAll('.nyc311-demo script').length}))));await page.locator('.nyc311-demo #source:not([hidden])').waitFor({timeout:15000});
  const status=await page.locator('.nyc311-demo #status').innerText();
  assert.doesNotMatch(status,/unavailable|error/i,'Live API request failed: '+status);
  const total=Number((await page.locator('.nyc311-demo #requests').innerText()).replaceAll(',',''));
  assert.ok(total>0,'Live request count must be positive');
  const options=await page.locator('.nyc311-demo #borough option').allTextContents();
  assert.ok(options.includes('Queens'),'Queens must be a filter option');
  await page.locator('.nyc311-demo #borough').selectOption('Queens');
  const queens=Number((await page.locator('.nyc311-demo #requests').innerText()).replaceAll(',',''));
  assert.ok(queens>0 && queens<total,'Queens subset must be nonempty and smaller than citywide');
  await page.locator('.nyc311-demo #reset').click();
  assert.equal(Number((await page.locator('.nyc311-demo #requests').innerText()).replaceAll(',','')),total);
  assert.equal(errors.length,0,'Page errors: '+errors.join('; '));
  console.log('PASS live NYC 311 source: '+total+' displayed requests; Queens: '+queens+'; '+status);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
