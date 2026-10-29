'use strict';
// Synthetic-only automated accessibility audit of rendered states.
// axe-core cannot establish WCAG conformance; native AT and human review remain required.
const assert = require('node:assert/strict');
const {createServer} = require('node:http');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const {chromium, firefox, webkit} = require('playwright');
const axe = require('axe-core');
const root = join(__dirname, '..');
const allowed = new Map([
  ['/', 'index.html'], ['/index.html', 'index.html'],
  ['/rescue-core.js', 'rescue-core.js'], ['/file-reader.js', 'file-reader.js'],
  ['/reconcile-core.js', 'reconcile-core.js'], ['/reconcile-ui.js', 'reconcile-ui.js']
]);
const server = createServer((req, res) => {
  const path = allowed.get(new URL(req.url, 'http://localhost').pathname);
  if (!path) { res.writeHead(404).end('Not found'); return; }
  try {
    res.writeHead(200, {'Content-Type':path.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8','Cache-Control':'no-store'});
    res.end(readFileSync(join(root, path)));
  } catch { res.writeHead(500).end('Unavailable'); }
});
const fixture = Buffer.from('ID,Note\n001,alpha\n002,\n003,=1+1\n001,alpha\n', 'utf8');
let checks = 0;
async function scan(page, name, state) {
  const result = await page.evaluate(async () => window.axe.run(document, {
    runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}
  }));
  const failures = result.violations.map(v => ({
    id:v.id, impact:v.impact, nodes:v.nodes.map(n=>n.target.join(' ')), description:v.help
  }));
  console.log(name+' '+state+': '+result.passes.length+' rules passed; '+result.incomplete.length+' require manual inspection; '+failures.length+' violations.');
  assert.deepEqual(failures, [], name+' '+state+' automated WCAG-tagged findings');
  checks++;
}
async function runEngine(type, name, url) {
  const browser = await type.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1280,height:800}});
    const external = [], errors = [];
    page.on('pageerror', e=>errors.push(e.message));
    page.on('request', r=>{if(!r.url().startsWith(url) && !r.url().startsWith('blob:'+url))external.push(r.url());});
    assert.equal((await page.goto(url,{waitUntil:'networkidle'})).status(),200); checks++;
    await page.addScriptTag({content:axe.source}); // Local injection; no CDN or user files.
    await scan(page,name,'empty');
    await page.locator('#file').setInputFiles({name:'invalid.txt',mimeType:'text/plain',buffer:Buffer.from('ID\n1\n')});
    await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('Choose a .csv or .tsv file'));
    await scan(page,name,'upload error');
    await page.locator('#file').setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:fixture});
    await page.waitForFunction(()=>document.querySelector('#previewStatus')?.textContent?.includes('4 source records'));
    await scan(page,name,'loaded with missing and duplicate');
    await page.locator('#previewFilter').selectOption('duplicates');
    await scan(page,name,'filtered duplicates');
    await page.locator('#previewJump').fill('5');
    await page.locator('#previewJump').press('Enter');
    assert.equal(await page.locator('#table .jump-target th[scope="row"]').innerText(),'5'); checks++;
    await scan(page,name,'focused jump target');
    await page.setViewportSize({width:320,height:800});
    await scan(page,name,'320px reflow');
    // Extend the same synthetic audit to the second-file/reconciliation workflow.
    // This catches accessible-state regressions that first-file-only scans miss.
    await page.setViewportSize({width:1280,height:800});
    await page.locator('#compareFile').setInputFiles({name:'invalid.txt',mimeType:'text/plain',buffer:Buffer.from('ID\\n1\\n')});
    await page.waitForFunction(()=>document.querySelector('#compareStatus')?.textContent?.includes('Choose a second .csv or .tsv file'));
    assert.equal(await page.locator('#compareStatus').getAttribute('role'),'alert'); checks++;
    assert.equal(await page.evaluate(()=>document.activeElement?.id),'compareStatus'); checks++;
    await scan(page,name,'second-file upload error');
    await page.locator('#compareFile').setInputFiles({
      name:'second-synthetic.csv',mimeType:'text/csv',
      buffer:Buffer.from('ID,Note\\n002,match\\n004,new\\n,missing\\n','utf8')
    });
    await page.waitForFunction(()=>document.querySelector('#compareStatus')?.textContent?.includes('Loaded second file'));
    assert.equal(await page.locator('#rightKey').isEnabled(),true); checks++;
    await scan(page,name,'second file loaded');
    await page.locator('#leftKey').selectOption('ID');
    await page.locator('#rightKey').selectOption('ID');
    assert.equal(await page.locator('#compareRun').isEnabled(),true); checks++;
    await page.locator('#compareRun').click();
    await page.waitForFunction(()=>document.querySelector('#compareStatus')?.textContent?.includes('Comparison complete'));
    assert.match(await page.locator('#compareStatus').innerText(),/1 exact one-to-one matches/); checks++;
    assert.match(await page.locator('#compareResults').innerText(),/002/); checks++;
    await scan(page,name,'reconciliation results');
    await page.locator('#compareResults').focus();
    assert.equal(await page.evaluate(()=>document.activeElement?.id),'compareResults'); checks++;
    await page.setViewportSize({width:320,height:800});
    await scan(page,name,'reconciliation results at 320px');
    await page.locator('#compareClear').click();
    assert.equal(await page.locator('#compareJson').isEnabled(),false); checks++;
    assert.equal(await page.locator('#rightKey').isEnabled(),false); checks++;
    await scan(page,name,'cleared reconciliation');
    assert.deepEqual(errors, [],name+' no JavaScript exceptions'); checks++;
    assert.deepEqual(external, [],name+' no off-origin requests'); checks++;
    await page.close();
  } finally {await browser.close();}
}
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const url='http://127.0.0.1:'+server.address().port+'/';
  try {
    for(const [name,type] of [['Chromium',chromium],['Firefox',firefox],['WebKit',webkit]]) await runEngine(type,name,url);
    console.log('PASS: '+checks+' synthetic browser checks including 33 dynamic axe-core state scans; NOT native screen-reader testing or WCAG certification.');
  } finally {await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
