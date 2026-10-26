import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { chromium, firefox, webkit } from 'playwright';
import { TOOLS } from './catalog.mjs';
import { filterTools } from './directory.mjs';

const browserName = process.argv[2] || 'chromium';
const engine = { chromium, firefox, webkit }[browserName];
if (!engine) throw new Error('Unknown browser engine');
const dir = dirname(fileURLToPath(import.meta.url));
const allowed = new Set(['index.html', 'app.mjs', 'catalog.mjs', 'directory.mjs', 'styles.css', 'layout.css', 'controls.css']);
const types = { '.html': 'text/html; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8' };
const server = createServer(async (req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  const name = pathname === '/' ? 'index.html' : pathname.slice(1);
  if (!allowed.has(name)) { res.writeHead(404); res.end('Not found'); return; }
  try {
    const data = await readFile(join(dir, name));
    const type = types[name.slice(name.lastIndexOf('.'))];
    res.writeHead(200, { 'Content-Type': type, 'X-Content-Type-Options': 'nosniff' });
    res.end(data);
  } catch { res.writeHead(500); res.end('Unable to load'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
let browser;
let checks = 0;
function equal(actual, expected, message) { assert.deepEqual(actual, expected, message); checks++; }
try {
  browser = await engine.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const response = await page.goto('http://127.0.0.1:' + server.address().port + '/', { waitUntil: 'networkidle' });
  equal(response.status(), 200, 'served HTML');
  equal(await page.title(), 'Find a Tool — Tools & Templates', 'page title');
  equal(await page.locator('main').count(), 1, 'main landmark');
  equal(await page.locator('a.skip[href="#ft15-directory"]').count(), 1, 'skip link');
  equal(await page.locator('#tool-count[role="status"][aria-live="polite"][aria-atomic="true"]').count(), 1, 'live result count');
  equal(await page.locator('.ft15-card').count(), TOOLS.length, 'all resources rendered');
  equal(await page.locator('.ft15-link').count(), TOOLS.filter(t => t.status === 'live').length, 'only live resources linked');
  const renderedLinks = await page.locator('.ft15-link').evaluateAll(links => links.map(a => a.href).sort());
  equal(renderedLinks, TOOLS.filter(t => t.status === 'live').map(t => t.url).sort(), 'exact approved live destinations');
  equal(await page.locator('.ft15-unavailable').count(), TOOLS.filter(t => t.status === 'development').length, 'development cards explicitly unavailable');
  equal(errors, [], 'no startup script errors');
  await page.evaluate(() => {
    const injected = document.createElement('script');
    injected.textContent = 'window.__ft15_untrusted_inline_executed = true';
    document.head.append(injected);
  });
  equal(await page.evaluate(() => Boolean(window.__ft15_untrusted_inline_executed)), false, 'HTML CSP blocks injected inline script');

  await page.locator('#tool-status').selectOption('development');
  equal(await page.locator('.ft15-card').count(), 11, 'development filter');
  equal(await page.locator('.ft15-link').count(), 0, 'development cards have no links');
  await page.locator('#tool-status').selectOption('live');
  equal(await page.locator('.ft15-card').count(), 6, 'live filter');
  await page.locator('#tool-query').fill('no-such-tool-987654');
  equal(await page.locator('.ft15-card').count(), 0, 'zero-results state');
  equal(await page.locator('.ft15-empty').count(), 1, 'zero-results guidance');
  equal(await page.locator('#tool-count').textContent(), '0 of 17 resources shown', 'announced empty count');
  await page.locator('#tool-clear').click();
  equal(await page.locator('.ft15-card').count(), 17, 'clear restores all cards');
  equal(await page.locator('#tool-query').inputValue(), '', 'clear resets query');
  equal(await page.locator('#tool-query').evaluate(el => el === document.activeElement), true, 'clear restores keyboard focus');
  await page.locator('#tool-query').fill('research evidence');
  const expectedMulti=filterTools(TOOLS,{query:'research evidence'}).map(t=>t.title).sort();
  equal(expectedMulti.length>0,true,'multi-term search has relevant results');
  equal((await page.locator('.ft15-card h3').allTextContents()).sort(),expectedMulti,'multi-term search across metadata');
  await page.locator('#tool-query').fill('EVIDENCE    RESEARCH');
  equal((await page.locator('.ft15-card h3').allTextContents()).sort(),expectedMulti,'word order and whitespace independent');
  await page.locator('#tool-query').fill('tExT   LeNs');
  equal(await page.locator('.ft15-card h3').allTextContents(),['Text Lens'],'case-insensitive multi-term search');

  // Real browser module execution with synthetic multilingual records; no user text leaves the page.
  const multilingual = await page.evaluate(async () => {
    const {filterTools} = await import('./directory.mjs');
    const fixture = [
      {id:'dev-marked',title:'किताब',category:'Language',description:'Hindi',status:'development'},
      {id:'dev-plain',title:'कतब',category:'Language',description:'Hindi',status:'development'},
      {id:'jp-voiced',title:'が',category:'Language',description:'Japanese',status:'development'},
      {id:'jp-plain',title:'か',category:'Language',description:'Japanese',status:'development'},
      {id:'latin',title:'Résumé',category:'Language',description:'Latin',status:'development'}
    ];
    const ids=query=>filterTools(fixture,{query}).map(x=>x.id);
    return {hindi:ids('किताब'),hindiPlain:ids('कतब'),
      voiced:ids('が'),decomposed:ids('か\u3099'),latin:ids('resume'),
      original:fixture[0].title};
  });
  equal(multilingual.hindi,['dev-marked'],'browser preserves Devanagari vowel sign');
  equal(multilingual.hindiPlain,['dev-plain'],'browser distinguishes unmarked Hindi');
  equal(multilingual.voiced,['jp-voiced'],'browser preserves Japanese dakuten');
  equal(multilingual.decomposed,['jp-voiced'],'browser matches canonical Japanese equivalent');
  equal(multilingual.latin,['latin'],'browser preserves Latin accent folding');
  equal(multilingual.original,'किताब','browser search does not mutate source');

  await page.locator('#tool-clear').click();
  const category = 'Research & Writing';
  await page.locator('#tool-category').selectOption(category);
  equal(await page.locator('.ft15-card').count(), filterTools(TOOLS, { category }).length, 'category filter uses canonical data');
  await page.locator('#tool-clear').click();

  await page.setViewportSize({ width: 320, height: 720 });
  equal(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true, '320 CSS px reflow');
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  const enlarged = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    labels: [...document.querySelectorAll('.ft15-filters label')].map(el => ({text:el.textContent.slice(0,35),w:el.clientWidth,scroll:el.scrollWidth,children:[...el.children].map(c=>({tag:c.tagName,w:c.clientWidth,scroll:c.scrollWidth,rect:Math.round(c.getBoundingClientRect().right)}))})),
    overflow: [...document.querySelectorAll('*')].filter(el => el.scrollWidth > el.clientWidth + 1 || el.getBoundingClientRect().right > innerWidth + 1).slice(0, 12).map(el => ({ tag: el.tagName, id: el.id, className: String(el.className).slice(0, 70), width: el.clientWidth, scroll: el.scrollWidth, left: Math.round(el.getBoundingClientRect().left), right: Math.round(el.getBoundingClientRect().right) }))
  }));
  equal(enlarged.scrollWidth <= enlarged.width, true, '200% root text enlargement reflow (not native browser zoom): ' + JSON.stringify(enlarged));
  equal(await page.locator('#tool-query').isVisible(), true, 'search remains visible on narrow screen');
  equal(errors, [], 'no runtime script errors');
  console.log('FT-15 ' + browserName + ' HTTP browser integration: ' + checks + '/' + checks + ' PASS');
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
