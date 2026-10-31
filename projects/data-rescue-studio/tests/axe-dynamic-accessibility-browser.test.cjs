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
  ['/reconcile-core.js', 'reconcile-core.js'], ['/comparison-issue-index.js', 'comparison-issue-index.js'],
  ['/reconcile-ui.js', 'reconcile-ui.js']
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
let checks = 0, scans = 0;
async function scan(page, name, state) {
  const result = await page.evaluate(async () => window.axe.run(document, {
    runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}
  }));
  const failures = result.violations.map(v => ({
    id:v.id, impact:v.impact, nodes:v.nodes.map(n=>n.target.join(' ')), description:v.help
  }));
  console.log(name+' '+state+': '+result.passes.length+' rules passed; '+result.incomplete.length+' require manual inspection; '+failures.length+' violations.');
  // Incomplete axe findings are not passes: retain the synthetic-only node
  // and rule details in CI so a human can inspect them before release.
  if (result.incomplete.length) {
    const manual = result.incomplete.map(rule=>({
      id:rule.id,
      nodes:rule.nodes.map(node=>({target:node.target,summary:(node.failureSummary||'').slice(0,240)}))
    }));
    console.log(name+' '+state+' manual accessibility review needed: '+JSON.stringify(manual));
  }
  assert.deepEqual(failures, [], name+' '+state+' automated WCAG-tagged findings');
  checks++;
  scans++;
}

// Supplement axe's inconclusive short/empty-cell contrast results with an
// independent computed-style check. This does not replace visual/AT review.
// W3C WCAG 2.2 SC 1.4.3: normal text requires at least 4.5:1.
async function auditReconciliationCells(page, name, state) {
  const result = await page.evaluate(() => {
    const parse = value => {
      const match = /^rgba?\(\s*(\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\s*\)$/.exec(value);
      return match ? [Number(match[1]), Number(match[2]), Number(match[3]), match[4] === undefined ? 1 : Number(match[4])] : null;
    };
    const luminance = color => {
      const c = color.slice(0, 3).map(v => {
        const s = v / 255;
        return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    };
    const ratio = (a, b) => {
      const x = luminance(a), y = luminance(b);
      return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
    };
    const errors = [], cells = [...document.querySelectorAll('#compareResults table th, #compareResults table td')];
    let populated = 0, empty = 0, minimum = Infinity;
    for (const [index, cell] of cells.entries()) {
      // Current renderer uses text nodes only. Fail closed if future markup
      // introduces nested styles or visual effects this check cannot measure.
      if (cell.children.length) { errors.push('cell ' + index + ': nested content'); continue; }
      const value = cell.textContent.trim();
      if (!value) { empty++; continue; }
      populated++;
      const style = getComputedStyle(cell), foreground = parse(style.color);
      if (!foreground || foreground[3] !== 1 || style.opacity !== '1' ||
          style.textShadow !== 'none') { errors.push('cell ' + index + ': unsupported text style'); continue; }
      let background = null;
      for (let node = cell; node && node.nodeType === 1; node = node.parentElement) {
        const computed = getComputedStyle(node), candidate = parse(computed.backgroundColor);
        if (computed.backgroundImage !== 'none' || computed.opacity !== '1' ||
            !candidate || (candidate[3] !== 0 && candidate[3] !== 1)) {
          errors.push('cell ' + index + ': unsupported background'); break;
        }
        if (candidate[3] === 1) { background = candidate; break; }
      }
      if (!background) { errors.push('cell ' + index + ': no opaque background'); continue; }
      const measured = ratio(foreground, background);
      minimum = Math.min(minimum, measured);
      if (measured < 4.5) errors.push('cell ' + index + ': contrast below 4.5:1');
    }
    return {cells: cells.length, populated, empty, minimum, errors};
  });
  assert.ok(result.cells >= 8, name + ' ' + state + ': table has data cells'); checks++;
  assert.ok(result.populated >= 8, name + ' ' + state + ': nonempty text checked'); checks++;
  assert.equal(result.empty, 0, name + ' ' + state + ': no unexplained empty preview cells'); checks++;
  assert.deepEqual(result.errors, [], name + ' ' + state + ': computed text/background contrast'); checks++;
  console.log(name + ' ' + state + ': ' + result.populated + ' populated cells checked; ' +
    result.empty + ' unlabeled blank cells; minimum computed contrast ' +
    result.minimum.toFixed(2) + ':1; manual rendered-state review still required.');
}

async function runEngine(type, name, url) {
  const browser = await type.launch({headless:true});
  try {
    const page = await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:800}});
    const external = [], errors = [];
    page.on('pageerror', e=>errors.push(e.message));
    page.on('request', r=>{if(!r.url().startsWith(url) && !r.url().startsWith('blob:'+url))external.push(r.url());});
    assert.equal((await page.goto(url,{waitUntil:'networkidle'})).status(),200); checks++;
    await page.addScriptTag({content:axe.source}); // Local injection; no CDN or user files.
    await scan(page,name,'empty');
    await page.locator('#file').setInputFiles({name:'invalid.txt',mimeType:'text/plain',buffer:Buffer.from('ID\n1\n')});
    await page.waitForFunction(()=>document.querySelector('#status')?.textContent?.includes('Choose a .csv or .tsv file'));
    assert.equal(await page.locator('#file').getAttribute('aria-describedby'),'status'); checks++;
    assert.equal(await page.locator('#file').getAttribute('aria-invalid'),'true'); checks++;
    assert.equal(await page.locator('#status').getAttribute('role'),'alert'); checks++;
    assert.equal(await page.locator('#status').getAttribute('aria-live'),'assertive'); checks++;
    assert.equal(await page.evaluate(()=>document.activeElement?.id),'status'); checks++;
    await scan(page,name,'upload error');
    await page.locator('#file').setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:fixture});
    await page.waitForFunction(()=>document.querySelector('#previewStatus')?.textContent?.includes('4 source records'));
    assert.equal(await page.locator('#file').getAttribute('aria-invalid'),null); checks++;
    assert.equal(await page.locator('#status').getAttribute('role'),'status'); checks++;
    assert.equal(await page.locator('#status').getAttribute('aria-live'),'polite'); checks++;
    await scan(page,name,'loaded with missing and duplicate');
    // An export failure is not a file-selection error: keep the valid input
    // accessible and avoid an incorrect invalid-file announcement.
    await page.evaluate(() => {
      window.__originalExportForStatusTest = window.DataRescue.exportCsvDownload;
      window.DataRescue.exportCsvDownload = () => {throw new Error('Synthetic export-only failure');};
    });
    await page.locator('#save').click();
    assert.match(await page.locator('#status').innerText(),/Synthetic export-only failure/); checks++;
    assert.equal(await page.locator('#status').getAttribute('role'),'alert'); checks++;
    assert.equal(await page.evaluate(()=>document.activeElement?.id),'status'); checks++;
    assert.equal(await page.locator('#file').getAttribute('aria-invalid'),null); checks++;
    assert.equal(await page.locator('#file').getAttribute('aria-describedby'),'status'); checks++;
    await page.evaluate(() => {
      window.DataRescue.exportCsvDownload = window.__originalExportForStatusTest;
      delete window.__originalExportForStatusTest;
    });
    const [recoveredCsv] = await Promise.all([
      page.waitForEvent('download'), page.locator('#save').click()
    ]);
    assert.equal(recoveredCsv.suggestedFilename(),'data-rescue-reviewed.csv'); checks++;
    assert.match(await page.locator('#status').innerText(),/CSV exported locally/); checks++;
    assert.equal(await page.locator('#status').getAttribute('role'),'status'); checks++;
    assert.equal(await page.locator('#file').getAttribute('aria-invalid'),null); checks++;
    assert.deepEqual(await page.locator('#columns table thead th').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('scope'))),['col','col','col','col']); checks++;
    assert.ok(await page.locator('#columns table tbody tr').count()>0); checks++;
    assert.equal(await page.locator('#columns table tbody tr').evaluateAll(rows=>rows.every(row=>row.firstElementChild?.tagName==='TH' && row.firstElementChild.getAttribute('scope')==='row' && [...row.children].slice(1).every(cell=>cell.tagName==='TD'))),true); checks++;
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
    await page.locator('#compareFile').setInputFiles({name:'invalid.txt',mimeType:'text/plain',buffer:Buffer.from('ID\n1\n')});
    await page.waitForFunction(()=>document.querySelector('#compareStatus')?.textContent?.includes('Choose a second .csv or .tsv file'));
    assert.equal(await page.locator('#compareStatus').getAttribute('role'),'alert'); checks++;
    assert.equal(await page.evaluate(()=>document.activeElement?.id),'compareStatus'); checks++;
    assert.equal(await page.locator('#compareFile').getAttribute('aria-invalid'),'true'); checks++;
    assert.equal(await page.locator('#compareFile').getAttribute('aria-describedby'),'compareStatus'); checks++;
    assert.equal(await page.locator('#compareStatus').getAttribute('aria-live'),'assertive'); checks++;
    await scan(page,name,'second-file upload error');
    await page.locator('#compareFile').setInputFiles({
      name:'malformed.csv',mimeType:'text/csv',buffer:Buffer.from([0x49,0x44,0x0A,0xC3])
    });
    await page.waitForFunction(()=>document.querySelector('#compareStatus')?.textContent?.includes('Invalid UTF-8'));
    assert.equal(await page.locator('#compareFile').getAttribute('aria-invalid'),'true'); checks++;
    assert.equal(await page.locator('#compareRun').isDisabled(),true); checks++;
    await scan(page,name,'second-file invalid UTF-8');
    await page.locator('#compareFile').setInputFiles({
      name:'second-synthetic.csv',mimeType:'text/csv',
      buffer:Buffer.from('ID,Note\n002,match\n004,new\n,missing\n','utf8')
    });
    await page.waitForFunction(()=>document.querySelector('#compareStatus')?.textContent?.includes('Loaded second file'));
    assert.equal(await page.locator('#compareFile').getAttribute('aria-invalid'),null); checks++;
    assert.equal(await page.locator('#compareStatus').getAttribute('role'),'status'); checks++;
    assert.equal(await page.locator('#compareStatus').getAttribute('aria-live'),'polite'); checks++;
    assert.equal(await page.locator('#rightKey').isEnabled(),true); checks++;
    await scan(page,name,'second file loaded');
    await page.locator('#leftKey').selectOption('ID');
    await page.locator('#rightKey').selectOption('ID');
    assert.equal(await page.locator('#compareRun').isEnabled(),true); checks++;
    await page.locator('#compareRun').click();
    await page.waitForFunction(()=>document.querySelector('#compareStatus')?.textContent?.includes('Comparison complete'));
    assert.match(await page.locator('#compareStatus').innerText(),/1 exact one-to-one matches/); checks++;
    assert.match(await page.locator('#compareResults').innerText(),/002/); checks++;
    assert.equal(await page.locator('#compareMetrics .metric').count(),9); checks++;
    assert.match(await page.locator('#compareStatus').innerText(),/Classified 4 of 4 first-file records and 3 of 3 second-file records/); checks++;
    // Simulate a reconciliation engine that silently omits one original record.
    // The UI must refuse to show or export a partial result, then recover.
    await page.evaluate(() => {
      window.__originalReconcileForCoverageTest = window.DataReconcile.reconcile;
      window.DataReconcile.reconcile = (...args) => ({
        ...window.__originalReconcileForCoverageTest(...args), missingRight:[]
      });
    });
    await page.locator('#compareRun').click();
    assert.match(await page.locator('#compareStatus').innerText(),/Incomplete source-record coverage/); checks++;
    assert.equal(await page.locator('#compareStatus').getAttribute('role'),'alert'); checks++;
    assert.equal(await page.locator('#compareMetrics .metric').count(),0); checks++;
    assert.equal(await page.locator('#compareResults table').count(),0); checks++;
    for (const id of ['compareExport','compareJson','compareIndex']) {
      assert.equal(await page.locator('#'+id).isEnabled(),false); checks++;
    }
    await page.evaluate(() => {
      window.DataReconcile.reconcile = window.__originalReconcileForCoverageTest;
      delete window.__originalReconcileForCoverageTest;
    });
    await page.locator('#compareRun').click();
    assert.equal(await page.locator('#compareIndex').isEnabled(),true); checks++;
    assert.equal(await page.locator('#compareMetrics .metric').count(),9); checks++;
    await scan(page,name,'reconciliation results');
    assert.equal(await page.locator('#comparePrev').isDisabled(),true); checks++;
    assert.equal(await page.locator('#compareNext').isDisabled(),true); checks++;
    assert.match(await page.locator('#comparePageStatus').innerText(),/Showing findings 1 through \d+ of \d+/); checks++;
    assert.deepEqual(await page.locator('#compareResults table thead th').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('scope'))),['col','col','col','col']); checks++;
    assert.ok(await page.locator('#compareResults table tbody tr').count()>0); checks++;
    assert.equal(await page.locator('#compareResults table tbody tr').evaluateAll(rows=>rows.every(row=>row.firstElementChild?.tagName==='TH' && row.firstElementChild.getAttribute('scope')==='row' && [...row.children].slice(1).every(cell=>cell.tagName==='TD'))),true); checks++;
    await auditReconciliationCells(page,name,'reconciliation results');
    const previewLabels = await page.locator('#compareResults tbody td').allTextContents();
    for (const label of ['Missing identifier','No first-file record','No second-file record']) {
      assert.ok(previewLabels.includes(label), name + ' explains ' + label); checks++;
    }
    const [exactAuditDownload] = await Promise.all([
      page.waitForEvent('download'), page.locator('#compareJson').click()
    ]);
    const exactAudit = JSON.parse(readFileSync(await exactAuditDownload.path(), 'utf8'));
    assert.deepEqual(exactAudit.missingRight, [4], name + ' exact audit retains source record'); checks++;
    for (const label of ['Missing identifier','No first-file record','No second-file record']) {
      assert.equal(JSON.stringify(exactAudit).includes(label), false, name + ' preview labels never enter exact audit'); checks++;
    }
    // If the CSV formula-risk validator fails, no download is permitted and
    // the error must be announced without an unhandled browser exception.
    let reconciliationCsvDownloads = 0;
    const countReconciliationCsv = download => {
      if (download.suggestedFilename() === 'data-rescue-comparison-audit.csv') reconciliationCsvDownloads++;
    };
    page.on('download', countReconciliationCsv);
    await page.evaluate(() => {
      window.__originalRiskForRecoveryTest = window.DataRescue.spreadsheetExportRisk;
      window.DataRescue.spreadsheetExportRisk = () => { throw new Error('Synthetic risk-check failure'); };
    });
    await page.locator('#compareExport').click();
    assert.match(await page.locator('#compareStatus').innerText(),/Unable to verify or export comparison CSV: Synthetic risk-check failure/); checks++;
    assert.match(await page.locator('#compareStatus').innerText(),/No CSV was downloaded/); checks++;
    assert.equal(await page.locator('#compareStatus').getAttribute('role'),'alert'); checks++;
    assert.equal(await page.evaluate(()=>document.activeElement?.id),'compareStatus'); checks++;
    assert.equal(reconciliationCsvDownloads,0); checks++;
    assert.deepEqual(errors,[],name+' risk validator error handled'); checks++;
    await page.evaluate(() => {
      window.DataRescue.spreadsheetExportRisk = window.__originalRiskForRecoveryTest;
      delete window.__originalRiskForRecoveryTest;
    });
    const [recoveredAuditCsv] = await Promise.all([
      page.waitForEvent('download'), page.locator('#compareExport').click()
    ]);
    assert.equal(recoveredAuditCsv.suggestedFilename(),'data-rescue-comparison-audit.csv'); checks++;
    assert.match(readFileSync(await recoveredAuditCsv.path(),'utf8'),/First file only/); checks++;
    assert.match(await page.locator('#compareStatus').innerText(),/Exported 5 findings/); checks++;
    page.off('download', countReconciliationCsv);
    assert.equal(await page.locator('#compareFindingFilter').isEnabled(),true); checks++;
    await page.locator('#compareFindingFilter').selectOption('ambiguous');
    assert.equal(await page.locator('#compareResults tbody tr').count(),1); checks++;
    assert.match(await page.locator('#comparePageStatus').innerText(),/findings overall/); checks++;
    await scan(page,name,'filtered ambiguous findings');
    await page.locator('#compareFindingFilter').selectOption('missing');
    assert.equal(await page.locator('#compareResults tbody tr').count(),1); checks++;
    await page.locator('#compareFindingFilter').selectOption('matches');
    assert.equal(await page.locator('#compareResults tbody tr').count(),1); checks++;
    await page.locator('#compareFindingFilter').selectOption('all');
    assert.equal(await page.locator('#compareResults tbody tr').count(),5); checks++;
    await page.locator('#compareIdentifier').fill('002');
    await page.locator('#compareIdentifier').press('Enter');
    assert.equal(await page.locator('#compareResults tbody tr').count(),1); checks++;
    assert.match(await page.locator('#comparePageStatus').innerText(),/for the exact identifier/); checks++;
    await scan(page,name,'exact identifier lookup');
    await page.locator('#compareIdentifier').fill('0002');
    await page.locator('#compareIdentifierFind').click();
    assert.equal(await page.locator('#compareResults tbody tr').count(),0); checks++;
    assert.match(await page.locator('#comparePageStatus').innerText(),/No reconciliation findings/); checks++;
    await page.locator('#compareIdentifierClear').click();
    assert.equal(await page.locator('#compareResults tbody tr').count(),5); checks++;
    assert.equal(await page.evaluate(()=>document.activeElement?.id),'compareIdentifier'); checks++;
    await page.setViewportSize({width:320,height:800});
    await scan(page,name,'identifier lookup 320px');
    await page.setViewportSize({width:1280,height:800});
    // Privacy-minimized export must retain exact source coverage, not identifier keys.
    assert.equal(await page.locator('#compareIndex').isEnabled(),true); checks++;
    const [indexDownload] = await Promise.all([
      page.waitForEvent('download'), page.locator('#compareIndex').click()
    ]);
    const index = JSON.parse(readFileSync(await indexDownload.path(), 'utf8'));
    assert.equal(index.format,'data-rescue-reconciliation-issue-index'); checks++;
    assert.equal(index.counts.firstRecords,4); checks++;
    assert.equal(index.counts.secondRecords,3); checks++;
    assert.deepEqual(index.findings.matches,[{firstSourceRecord:3,secondSourceRecord:2}]); checks++;
    assert.deepEqual(index.findings.ambiguous,[{firstSourceRecords:[2,5],secondSourceRecords:[]}]); checks++;
    assert.deepEqual(index.findings.firstOnly,[4]); checks++;
    assert.deepEqual(index.findings.secondOnly,[3]); checks++;
    assert.deepEqual(index.findings.missingSecondKey,[4]); checks++;
    assert.equal(/synthetic\\.csv|second-synthetic|=1\\+1|alpha|"key":|"fileName":/.test(JSON.stringify(index)),false); checks++;
    assert.match(await page.locator('#compareStatus').innerText(),/No identifier keys, filenames or cell values/); checks++;
    const invalid = await page.evaluate(() => {
      const result={matches:[{key:'SECRET',leftRow:2,rightRow:2}],ambiguous:[],
        leftOnly:[],rightOnly:[],missingLeft:[],missingRight:[]};
      const build=window.DataRescueComparisonIndex.create;
      const rejected=(a,b,c)=>{try{build(a,b,c);return false;}catch{return true;}};
      return [
        rejected(result,[2,2],[2]), // repeated source identifier
        rejected(result,[2,3],[2]), // incomplete source coverage
        rejected({...result,missingLeft:[2]},[2],[2]), // duplicate coverage
        rejected({...result,matches:[{key:'SECRET',leftRow:999,rightRow:2}]},[2],[2]), // unknown source
        !build(result,[2],[2]).includes('SECRET') // never copy raw identifier
      ];
    });
    assert.deepEqual(invalid,[true,true,true,true,true]); checks++;

    await page.locator('#compareResults').focus();
    assert.equal(await page.evaluate(()=>document.activeElement?.id),'compareResults'); checks++;
    await page.setViewportSize({width:320,height:800});
    await scan(page,name,'reconciliation results at 320px');
    await auditReconciliationCells(page,name,'reconciliation results at 320px');
    const narrowLabels = await page.locator('#compareResults tbody td').allTextContents();
    for (const label of ['Missing identifier','No first-file record','No second-file record']) {
      assert.ok(narrowLabels.includes(label), name + ' 320px retains ' + label); checks++;
    }
    await page.locator('#compareClear').click();
    assert.equal(await page.locator('#comparePrev').isDisabled(),true); checks++;
    assert.equal(await page.locator('#compareNext').isDisabled(),true); checks++;
    assert.equal(await page.locator('#compareJson').isEnabled(),false); checks++;
    assert.equal(await page.locator('#compareFindingFilter').isDisabled(),true); checks++;
    assert.equal(await page.locator('#compareIndex').isEnabled(),false); checks++;
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
    console.log('PASS: '+checks+' synthetic browser checks including '+scans+' dynamic axe-core state scans; NOT native screen-reader testing or WCAG certification.');
  } finally {await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
