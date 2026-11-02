const { chromium } = require('playwright');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
 const browser = await chromium.launch({headless:true});
 try {
  const page = await browser.newPage();
  const errors=[]; page.on('pageerror', e=>errors.push(e.message));
  await page.goto('file://' + path.resolve(__dirname,'interactive-preview.html'));
  await page.getByRole('heading',{name:'NYC 311 Public Service Operations Explorer'}).waitFor();
  assert.match(await page.locator('.notice').innerText(),/fabricated test aggregates/i);
  const total=await page.locator('#requests').innerText();
  assert.ok(Number(total.replaceAll(',',''))>0);
  assert.equal(await page.locator('#rows tr').count(),3);
  await page.getByLabel('Borough').selectOption('Queens');
  const queens=await page.locator('#requests').innerText();
  assert.notEqual(queens,total);
  await page.getByLabel('Month').selectOption('2026-09');
  await page.getByLabel('Problem',{exact:true}).selectOption('Noise');
  assert.equal(await page.locator('#rows tr').count(),1);
  assert.match(await page.locator('#status').innerText(),/1 synthetic aggregate groups/);
  assert.match(await page.locator('#bars').getAttribute('aria-label'),/Noise: /);
  await page.getByRole('button',{name:'Reset filters'}).click();
  assert.equal(await page.locator('#requests').innerText(),total);
  assert.equal(await page.locator('#rows tr').count(),3);
  assert.deepEqual(errors,[]);
  console.log('PASS: synthetic disclosure, filtering, live status, chart text alternative, table and reset');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
