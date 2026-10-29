'use strict';
// Synthetic, HTTP-served browser test for CSS-zoom stress and keyboard reflow.
// CSS zoom is NOT the browser's native zoom control, nor a WCAG conformance test.
const assert = require('node:assert/strict');
const {createServer} = require('node:http');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const {chromium, firefox, webkit} = require('playwright');

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
    res.writeHead(200, {
      'Content-Type': path.endsWith('.html') ? 'text/html; charset=utf-8' : 'text/javascript; charset=utf-8',
      'Cache-Control': 'no-store'
    });
    res.end(readFileSync(join(root, path)));
  } catch { res.writeHead(500).end('Unavailable'); }
});
const rows = ['ID,Note', '01,first', '02,'];
for (let i = 3; i <= 46; i++) rows.push(String(i).padStart(2, '0') + ',value-' + i);
rows.push('01,first');
const fixture = Buffer.from(rows.join('\n') + '\n', 'utf8');
let checks = 0;
function eq(actual, expected, message) { assert.deepEqual(actual, expected, message); checks++; }
function ok(value, message) { assert.ok(value, message); checks++; }

async function review(browserType, name, scale, url) {
  const browser = await browserType.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1280,height:800},acceptDownloads:true});
    const errors = [], external = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {
      if (!request.url().startsWith(url) && !request.url().startsWith('blob:' + url))
        external.push(request.url());
    });
    eq((await page.goto(url, {waitUntil:'networkidle'})).status(), 200, name + ' served page');
    await page.evaluate(value => { document.documentElement.style.zoom = String(value); }, scale);
    const initial = await page.evaluate(() => ({
      zoom: getComputedStyle(document.documentElement).zoom,
      client: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth
    }));
    eq(Number(initial.zoom), scale, name + ' applied CSS zoom stress factor');
    ok(initial.client > 0, name + ' CSS zoom probe has measurable layout');
    // Root CSS zoom does not consistently resize the layout viewport across engines.
    // Reset it and test W3C's 640/320 CSS-pixel zoom-equivalent widths explicitly.
    await page.evaluate(() => { document.documentElement.style.zoom = '1'; });
    await page.setViewportSize({width:Math.round(1280 / scale),height:800});
    const equivalent = await page.evaluate(() => ({client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
    ok(equivalent.client <= Math.round(1280 / scale) + 1, name + ' zoom-equivalent viewport width');
    ok(equivalent.scroll <= equivalent.client + 1, name + ' upload controls reflow without page-level horizontal overflow');

    await page.locator('#file').setInputFiles({
      name:'synthetic-invalid.txt', mimeType:'text/plain', buffer:Buffer.from('ID\n1\n')
    });
    await page.waitForFunction(() => document.querySelector('#status')?.textContent?.includes('Choose a .csv or .tsv file'));
    eq(await page.locator('#status').getAttribute('role'), 'alert', name + ' error announced at zoom');
    ok(await page.locator('#status').evaluate(el => document.activeElement === el), name + ' error receives focus');
    eq(await page.locator('#file').getAttribute('aria-invalid'), 'true', name + ' invalid upload identified');

    await page.locator('#file').setInputFiles({
      name:'synthetic-zoom.csv', mimeType:'text/csv', buffer:fixture
    });
    await page.waitForFunction(() => document.querySelector('#previewStatus')?.textContent?.includes('47 source records'));
    eq(await page.locator('#file').getAttribute('aria-invalid'), null, name + ' valid retry clears error');
    ok(await page.locator('#saveIssues').isEnabled(), name + ' issue index available');
    const loaded = await page.evaluate(() => ({
      client: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
      zoom: Number(getComputedStyle(document.documentElement).zoom)
    }));
    eq(loaded.zoom, 1, name + ' equivalent viewport uses native CSS layout');
    ok(loaded.scroll <= loaded.client + 1, name + ' loaded interface reflows without page-level horizontal overflow');

    await page.locator('#previewJump').fill('48');
    await page.locator('#previewJump').press('Enter');
    const target = page.locator('#table .jump-target th[scope="row"]');
    eq(await target.innerText(), '48', name + ' final source record navigable');
    ok(await target.evaluate(el => document.activeElement === el), name + ' jump focuses original record');
    eq(await target.getAttribute('aria-label'), 'Source record 48, jump target', name + ' accessible target name preserved');

    const [download] = await Promise.all([
      page.waitForEvent('download'), page.locator('#saveIssues').click()
    ]);
    const index = JSON.parse(readFileSync(await download.path(), 'utf8'));
    eq(index.recordCount, 47, name + ' complete record coverage at zoom');
    eq(index.issues, [
      {sourceRecord:3,blankColumns:[2],duplicateOf:null},
      {sourceRecord:48,blankColumns:[],duplicateOf:2}
    ], name + ' missing and duplicate source positions unchanged');
    ok(!Object.hasOwn(index.source, 'fileName') && !Object.hasOwn(index.source, 'sha256'),
      name + ' privacy defaults unaffected by zoom');

    await page.locator('#previewFilter').selectOption('missing');
    await page.locator('#previewJump').fill('48');
    await page.locator('#previewJump').press('Enter');
    eq(await page.locator('#previewJump').getAttribute('aria-invalid'), 'true',
      name + ' filtered-out record error remains accessible');
    ok(await page.locator('#previewJump').evaluate(el => document.activeElement === el),
      name + ' invalid jump returns focus');
    await page.locator('#previewJump').fill('3');
    await page.locator('#previewJump').press('Enter');
    eq(await page.locator('#table .jump-target th[scope="row"]').innerText(), '3',
      name + ' keyboard recovery selects missing-value source');

    await page.locator('#reset').focus();
    await page.keyboard.press('Enter');
    eq(await page.locator('#status').innerText(), 'No data loaded.', name + ' keyboard clear works');
    ok(await page.locator('#saveIssues').isDisabled(), name + ' clear disables index export');
    ok(!await page.locator('#issueIncludeSource').isChecked(), name + ' clear resets metadata opt-in');
    const cleared = await page.evaluate(() => ({
      client: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth
    }));
    ok(cleared.scroll <= cleared.client + 1, name + ' cleared interface reflows');
    eq(errors, [], name + ' no page errors');
    eq(external, [], name + ' no off-origin requests');
    await page.close();
  } finally { await browser.close(); }
}

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const url = 'http://127.0.0.1:' + server.address().port + '/';
  try {
    for (const [name, type] of [['Chromium', chromium], ['Firefox', firefox], ['WebKit', webkit]]) {
      for (const scale of [2, 4]) await review(type, name + ' CSS ' + (scale * 100) + '%', scale, url);
    }
    console.log('PASS: ' + checks + ' synthetic CSS-zoom stress assertions across Chromium, Firefox and WebKit');
    console.log('NOTE: CSS zoom is probed then reset; functional checks use 640/320 CSS-pixel zoom-equivalent viewports, NOT native browser zoom, physical device or screen-reader verification.');
  } finally { await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
