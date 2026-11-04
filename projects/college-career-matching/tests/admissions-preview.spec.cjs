const { chromium } = require('playwright');
const AxeBuilder = require('@axe-core/playwright').default;
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:390,height:844}});
    await page.goto('file://' + path.resolve(__dirname,'../admissions-evidence-review.html'));
    await assert.equal(await page.locator('h1').count(),1);
    for(const [key,expected] of [['generic','Generic BS in Nursing'],['accelerated','Accelerated Second-Degree BS (A2D)'],['rn','RN-to-BS completion']]){
      await page.locator('#route').selectOption(key);
      assert.equal(await page.locator('#name').innerText(),expected);
      assert.match(await page.locator('#status').innerText(),new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
      assert.match(await page.locator('#source').getAttribute('href'),/^https:\/\/www\.hunter\.cuny\.edu\//);
    }
    await page.locator('#route').selectOption('rn');
    assert.match(await page.locator('#requirement').innerText(),/not been independently established/);
    const result=await new AxeBuilder({page}).analyze();
    const serious=result.violations.filter(v=>['critical','serious'].includes(v.impact));
    assert.deepEqual(serious.map(v=>v.id),[],JSON.stringify(serious));
    await page.keyboard.press('Tab');
    console.log('PASS: three pathways, source routing, evidence containment, mobile axe serious/critical = 0');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
