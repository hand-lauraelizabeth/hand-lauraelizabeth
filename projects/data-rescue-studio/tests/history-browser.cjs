const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url'),{chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch();
 const page=await browser.newPage({acceptDownloads:true,viewport:{width:320,height:780}});
 let n=0;const ok=(v,s)=>{assert.ok(v,s);n++;};
 try{
  await page.goto(pathToFileURL(path.resolve(__dirname,'../history-preview.html')).href);
  await page.locator('#sample').click();
  await page.locator('#trimColumn').selectOption('1');
  await page.locator('#trimApply').click();
  ok((await page.locator('#historyStatus').innerText()).includes('Trimmed 3'),'trim history');
  await page.locator('#removeDuplicates').click();
  ok((await page.locator('#rowCount').innerText()).includes('2 current'),'dedupe applied');
  await page.locator('#historyUndo').click();
  ok((await page.locator('#rowCount').innerText()).includes('3 current'),'undo restores');
  await page.locator('#historyRedo').click();
  ok((await page.locator('#rowCount').innerText()).includes('2 current'),'redo reapplies');
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#save').click()]);
  ok(fs.readFileSync(await download.path(),'utf8').includes('"Ada"'),'working CSV');
  const [manifest]=await Promise.all([page.waitForEvent('download'),page.locator('#historyExport').click()]);
  const data=JSON.parse(fs.readFileSync(await manifest.path(),'utf8'));
  ok(data.steps.length===2&&data.exports.length===1,'manifest steps and export');
  ok(!JSON.stringify(data).includes(' Ada '),'no raw name values in manifest');
  ok((await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth))<=1,'320px fits');
  await page.locator('#reset').click();
  ok(await page.locator('#historyUndo').isDisabled(),'reset clears undo');
  console.log('PASS: '+n+' Chromium history preview assertions.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});