const { chromium } = require('playwright');
const assert = require('node:assert/strict');

const url = 'https://raw.githack.com/hand-lauraelizabeth/hand-lauraelizabeth/release/workforce-interactive-preview-20261102/projects/workforce-opportunity-explorer/interactive-preview.html';

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    assert.equal(response?.status(), 200, 'Hosted preview HTTP status');
    const title = await page.title();
    if (/External Content Notice/i.test(title)) {
      // The third-party preview proxy displays an interstitial before serving HTML.
      // Follow only its explicit Open the page link; never count the notice as the app.
      const notice = page.getByRole('link', { name: 'Open the page', exact: true });
      assert.equal(await notice.count(), 1, 'Expected one explicit preview consent link');
      console.log('HOSTED INTERSTITIAL', JSON.stringify({
        title,
        destination: await notice.getAttribute('href')
      }));
      await Promise.all([
        page.waitForLoadState('domcontentloaded'),
        notice.click({ timeout: 15000 })
      ]);
    }
    console.log('HOSTED CONTENT', JSON.stringify({
      url: page.url(),
      title: await page.title(),
      body: (await page.locator('body').innerText()).slice(0,300)
    }));
    await page.screenshot({
      path: 'projects/workforce-opportunity-explorer/hosted-preview-smoke.png',
      fullPage: true
    });
    await page.getByRole('heading', {
      name: 'Workforce Opportunity & Skills Intelligence Explorer'
    }).waitFor({ timeout: 15000 });
    assert.doesNotMatch(await page.title(), /External Content Notice/i);
    assert.match(await page.locator('#source-label').innerText(), /FICTIONAL DEMONSTRATION/);
    assert.equal(await page.locator('#rows tr').count(), 12);
    await page.locator('#compare-soc').selectOption('15-2051');
    await page.locator('#compare-a').selectOption('Fictional Metro North');
    await page.locator('#compare-b').selectOption('Fictional Metro South');
    assert.match(await page.locator('#compare-result').innerText(), /11,000/);
    await page.locator('#group').selectOption('Healthcare');
    assert.equal(await page.locator('#rows tr').count(), 3);
    await page.screenshot({
      path: 'projects/workforce-opportunity-explorer/hosted-preview-smoke.png',
      fullPage: true
    });
    assert.deepEqual(errors, []);
    console.log('PASS hosted Workforce preview: fictional provenance, 12 rows, matched-SOC comparison, group filter, no page errors', page.url());
  } finally {
    await browser.close();
  }
})().catch(e => { console.error('HOSTED PREVIEW BLOCKER:', e); process.exit(1); });
