const {chromium}=require('playwright');
const path=require('node:path');
const assert=require('node:assert/strict');
const fixtures=[
 {borough:'BRONX',complaint_type:'Noise - Residential',status:'Closed',requests:'40'},
 {borough:'BRONX',complaint_type:'Noise - Residential',status:'Open',requests:'30'},
 {borough:'QUEENS',complaint_type:'Noise - Residential',status:'Closed',requests:'60'},
 {borough:'QUEENS',complaint_type:'Noise - Residential',status:'Open',requests:'50'},
 {borough:'BROOKLYN',complaint_type:'Illegal Parking',status:'Closed',requests:'120'},
 {borough:'MANHATTAN',complaint_type:'Noise - Residential',status:'Closed',requests:'70'},
 {borough:'STATEN ISLAND',complaint_type:'Rodent',status:'Closed',requests:'30'},
 {borough:'QUEENS',complaint_type:'Street Condition',status:'Open',requests:'5'}
];
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage();
  const errors=[];let apiCalls=0;page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/resource/erm2-nwe9.json?**',route=>{apiCalls++;return route.fulfill({status:200,contentType:'application/json',headers:{'access-control-allow-origin':'*'},body:JSON.stringify(fixtures)});});
  await page.goto('file://'+path.resolve(__dirname,'interactive-preview.html'));
  await page.locator('#source:not([hidden])').waitFor({timeout:10000});
  assert.match(await page.locator('.notice').innerText(),/Live public data/i);
  assert.equal(await page.locator('#requests').innerText(),'400');
  assert.equal(await page.locator('#closed').innerText(),'320');
  assert.equal(await page.locator('#rows tr').count(),3);
  assert.equal(await page.locator('#borough-bars .barrow').count(),5);
  await page.getByLabel('Borough').selectOption('Queens');
  assert.equal(await page.locator('#requests').innerText(),'110');
  await page.getByLabel('Problem',{exact:true}).selectOption('Noise - Residential');
  assert.equal(await page.locator('#rows tr').count(),1);
  assert.match(await page.locator('#borough-bars').getAttribute('aria-label'),/Queens: 110 requests/);
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:/Export filtered aggregates/}).click();
  assert.match((await download).suggestedFilename(),/\.csv$/);
  await page.getByRole('button',{name:'Reset filters'}).click();
  assert.equal(await page.locator('#requests').innerText(),'400');
  await page.getByLabel('Reporting window').selectOption('30');
  await page.locator('#source:not([hidden])').waitFor();
  assert.ok(apiCalls>=2);
  assert.deepEqual(errors,[]);
  console.log('PASS: mocked API aggregate groups, uppercase borough normalization, small-cell exclusion, interactive charts, CSV and reset');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
