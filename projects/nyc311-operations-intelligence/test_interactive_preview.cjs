const { chromium } = require('playwright');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
 const browser = await chromium.launch({headless:true});
 try {
  const page = await browser.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const fixture=[];
  for(const borough of ['Queens','Bronx'])for(const complaint_type of ['Noise','Street condition'])for(const status of ['Closed','Open'])fixture.push({borough,complaint_type,status,requests:status==='Closed'?'75':'25'});
  let calls=0;
  await page.route('https://data.cityofnewyork.us/resource/erm2-nwe9.json?*',async route=>{calls++;await route.fulfill({status:200,contentType:'application/json',headers:{'access-control-allow-origin':'*'},body:JSON.stringify(fixture)});});
  await page.goto('file://'+path.resolve(__dirname,'interactive-preview.html'));
  await page.getByRole('heading',{name:'NYC 311 Public Service Operations Explorer'}).waitFor();
  await page.waitForFunction(()=>document.querySelector('#requests').textContent!=='—');
  assert.match(await page.locator('.notice').innerText(),/Live public data/i);
  assert.equal(await page.locator('#requests').innerText(),'400');
  assert.equal(await page.locator('#closed').innerText(),'300');
  assert.equal(await page.locator('#rows tr').count(),2);
  await page.getByLabel('Borough').selectOption('Queens');
  assert.equal(await page.locator('#requests').innerText(),'200');
  await page.getByLabel('Problem',{exact:true}).selectOption('Noise');
  assert.equal(await page.locator('#requests').innerText(),'100');
  await page.getByRole('button',{name:'Reset filters'}).click();
  assert.equal(await page.locator('#requests').innerText(),'400');
  await page.getByRole('button',{name:'Refresh live data'}).click();
  await page.waitForFunction(()=>document.querySelector('#requests').textContent==='400');
  assert.ok(calls>=2);
  assert.deepEqual(errors,[]);
  console.log('PASS: API-mocked browser render, filters, summary, chart, table, reset, refresh');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
