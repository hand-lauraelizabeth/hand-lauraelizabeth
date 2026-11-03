const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const url='https://raw.githack.com/hand-lauraelizabeth/hand-lauraelizabeth/release/nyc311-interactive-preview-20261102/projects/nyc311-operations-intelligence/interactive-preview.html';
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  let apiCalls=0;
  await page.route('https://data.cityofnewyork.us/resource/erm2-nwe9.json?*',async route=>{
   apiCalls++;
   const q=new URL(route.request().url()).searchParams;
   const data=q.get('$group')==='incident_zip'?[{incident_zip:'11354',requests:'44'},{incident_zip:'11355',requests:'9'}]:[{borough:'QUEENS',complaint_type:'Noise - Residential',status:'Closed',requests:'75'},{borough:'QUEENS',complaint_type:'Noise - Residential',status:'Open',requests:'25'},{borough:'BRONX',complaint_type:'HEAT/HOT WATER',status:'Closed',requests:'40'}];
   await route.fulfill({status:200,contentType:'application/json',headers:{'access-control-allow-origin':'*'},body:JSON.stringify(data)});
  });
  const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
  assert.equal(response?.status(),200,'Hosted URL must respond HTTP 200');
  if(/External Content Notice/i.test(await page.title())){
   const consent=page.getByText('Open the page',{exact:true}).first();
   assert.equal(await consent.count(),1,'Preview proxy must expose consent');
   await consent.click({timeout:15000});
  }
  await page.getByRole('heading',{name:'NYC 311 Public Service Operations Explorer'}).waitFor({timeout:20000});
  assert.doesNotMatch(await page.title(),/External Content Notice/,'Interstitial is not the application');
  await page.waitForFunction(()=>document.querySelector('#requests')?.textContent==='140');
  assert.match(await page.locator('#source').innerText(),/LIVE NYC Open Data/);
  await page.getByLabel('Borough',{exact:true}).selectOption('Queens');
  assert.equal(await page.locator('#requests').innerText(),'100');
  await page.getByRole('button',{name:'Try fictional example (offline)'}).click();
  assert.equal(await page.locator('#requests').innerText(),'160');
  assert.match(await page.locator('#source').innerText(),/FICTIONAL EXAMPLE/);
  await page.getByRole('button',{name:'Load ZIP comparison'}).click();
  await page.waitForFunction(()=>document.querySelector('#geo-message').textContent.includes('Top 1 ZIP'));
  assert.equal(await page.locator('#geo-table tr').count(),1,'Suppress ZIP counts under 20');
  await page.locator('#geo-type').selectOption('housing');
  assert.equal(await page.locator('#geo-table tr').count(),0,'Changing category clears stale ZIP results');
  await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});
  const axe=await page.evaluate(async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}}));
  const serious=axe.violations.filter(v=>['critical','serious'].includes(v.impact));
  assert.deepEqual(serious.map(v=>({id:v.id,impact:v.impact,targets:v.nodes.map(n=>n.target)})),[],'No serious/critical axe violations');
  assert.deepEqual(errors,[],'No browser page errors');
  assert.ok(apiCalls>=2,'Hosted application must execute real interactive fetch logic (mocked source)');
  console.log('PASS hosted NYC311: application (not interstitial), borough filter, fictional mode, ZIP suppression, stale-state reset, mobile axe, no JS errors');
 }finally{await browser.close();}
})().catch(e=>{console.error('HOSTED NYC311 PREVIEW BLOCKER:',e);process.exit(1);});
