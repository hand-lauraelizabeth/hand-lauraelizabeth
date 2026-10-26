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
const allowed = new Set(['index.html', 'app.mjs', 'catalog.mjs', 'directory.mjs', 'styles.css', 'layout.css', 'controls.css', 'focus.css']);
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
  // Oversized paste must fail closed without truncating the entered text.
  await page.locator('#tool-query').fill('a'.repeat(257));
  equal(await page.locator('#tool-query').inputValue(),'a'.repeat(257),'oversized paste remains editable, not silently truncated');
  equal(await page.locator('#tool-query').getAttribute('aria-invalid'),'true','oversized query identified as invalid');
  equal(await page.locator('#tool-query').getAttribute('aria-describedby'),'tool-query-error','error associated with search input');
  equal(await page.locator('#tool-query-error[role="alert"]').isVisible(),true,'oversized query has visible alert');
  equal(await page.locator('.ft15-card').count(),0,'invalid query does not render partial results');
  equal(await page.locator('#tool-count').textContent(),'Search paused until the query is shortened','invalid query announced in status');
  await page.locator('#tool-query').fill('text lens');
  equal(await page.locator('#tool-query-error').isHidden(),true,'correcting query clears alert');
  equal(await page.locator('#tool-query').getAttribute('aria-invalid'),null,'corrected query clears error state');
  equal(await page.locator('.ft15-card h3').allTextContents(),['Text Lens'],'normal search recovers');
  await page.locator('#tool-query').fill('🧪'.repeat(256));
  equal(await page.locator('#tool-query-error').isHidden(),true,'256 supplementary characters allowed');
  await page.locator('#tool-query').fill('🧪'.repeat(257));
  equal(await page.locator('#tool-query-error').isVisible(),true,'257 supplementary characters rejected');
  await page.locator('#tool-clear').click();
  equal(await page.locator('.ft15-card').count(),TOOLS.length,'clear restores all after invalid query');
  equal(await page.locator('#tool-query').evaluate(el=>el===document.activeElement),true,'clear restores focus after invalid query');
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
      {id:'gr-accent',title:'ά',category:'Language',description:'Greek',status:'development'},
      {id:'gr-plain',title:'α',category:'Language',description:'Greek',status:'development'},
      {id:'ar-vowel',title:'عَلَم',category:'Language',description:'Arabic',status:'development'},
      {id:'ar-plain',title:'علم',category:'Language',description:'Arabic',status:'development'},
      {id:'latin',title:'Résumé',category:'Language',description:'Latin',status:'development'}
    ];
    const ids=query=>filterTools(fixture,{query}).map(x=>x.id);
    return {hindi:ids('किताब'),hindiPlain:ids('कतब'),hindiBare:ids('क'),
      voiced:ids('が'),unvoiced:ids('か'),decomposed:ids('か\u3099'),
      greekAccent:ids('ά'),greekPlain:ids('α'),
      arabicVowel:ids('عَ'),arabicPlain:ids('ع'),
      latin:ids('resume'),original:fixture[0].title};
  });
  equal(multilingual.hindi,['dev-marked'],'browser preserves Devanagari vowel sign');
  equal(multilingual.hindiPlain,['dev-plain'],'browser distinguishes unmarked Hindi');
  equal(multilingual.voiced,['jp-voiced'],'browser preserves Japanese dakuten');
  equal(multilingual.unvoiced,['jp-plain'],'browser excludes voiced Japanese grapheme from unvoiced search');
  equal(multilingual.hindiBare,['dev-plain'],'browser excludes Hindi vowelled grapheme from bare consonant search');
  equal(multilingual.greekAccent,['gr-accent'],'browser retains Greek accent');
  equal(multilingual.greekPlain,['gr-plain'],'browser excludes accented Greek grapheme from plain search');
  equal(multilingual.arabicVowel,['ar-vowel'],'browser retains Arabic vowel mark');
  equal(multilingual.arabicPlain,['ar-plain'],'browser excludes vowelled Arabic grapheme from plain search');
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
  await page.locator('#tool-query').fill('x'.repeat(257));
  equal(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth),true,'visible query error reflows at 320px');
  equal(await page.locator('#tool-query-error').isVisible(),true,'narrow-screen query error remains visible');
  await page.locator('#tool-clear').click();
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  const enlarged = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    labels: [...document.querySelectorAll('.ft15-filters label')].map(el => ({text:el.textContent.slice(0,35),w:el.clientWidth,scroll:el.scrollWidth,children:[...el.children].map(c=>({tag:c.tagName,w:c.clientWidth,scroll:c.scrollWidth,rect:Math.round(c.getBoundingClientRect().right)}))})),
    overflow: [...document.querySelectorAll('*')].filter(el => el.scrollWidth > el.clientWidth + 1 || el.getBoundingClientRect().right > innerWidth + 1).slice(0, 12).map(el => ({ tag: el.tagName, id: el.id, className: String(el.className).slice(0, 70), width: el.clientWidth, scroll: el.scrollWidth, left: Math.round(el.getBoundingClientRect().left), right: Math.round(el.getBoundingClientRect().right) }))
  }));
  equal(enlarged.scrollWidth <= enlarged.width, true, '200% root text enlargement reflow (not native browser zoom): ' + JSON.stringify(enlarged));
  // W3C WCAG 2.2 1.4.10 and 1.4.4: stress-test 400% root text
  // at 320 CSS px. This is text enlargement, NOT native browser zoom.
  await page.evaluate(() => { document.documentElement.style.fontSize = '400%'; });
  const fourfold = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    controls: [...document.querySelectorAll('#tool-query,#tool-category,#tool-status,#tool-clear')]
      .map(el => ({ id:el.id, visible:el.getBoundingClientRect().width>0 && el.getBoundingClientRect().height>0,
        left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right }))
  }));
  equal(fourfold.scrollWidth <= fourfold.width, true,
    '400% root text / 320px reflow (not native zoom): '+JSON.stringify(fourfold));
  equal(fourfold.controls.every(c=>c.visible && c.left>=-1 && c.right<=fourfold.width+1),true,
    '400% root text keeps all four filters onscreen: '+JSON.stringify(fourfold));
  await page.locator('#tool-query').fill('text lens');
  equal(await page.locator('.ft15-card h3').allTextContents(),['Text Lens'],
    'search remains operable at 400% root text');
  await page.locator('#tool-clear').click();
  equal(await page.locator('.ft15-card').count(),TOOLS.length,
    'clear remains operable at 400% root text');
  equal(await page.locator('#tool-query').isVisible(), true, 'search remains visible on narrow screen');
  // Chromium emulates the Windows-style forced-colors preference; this is not
  // a physical Windows High Contrast or assistive-technology certification.
  if (browserName === 'chromium') {
    await page.emulateMedia({ forcedColors: 'active' });
    equal(await page.evaluate(() => matchMedia('(forced-colors: active)').matches), true,
      'Chromium forced-colors preference is active');
    const highContrast = await page.evaluate(() => {
      const link = document.querySelector('.ft15-link');
      const badge = document.querySelector('.ft15-badge');
      const linkStyle = getComputedStyle(link), badgeStyle = getComputedStyle(badge);
      return {
        linkBorder: parseFloat(linkStyle.borderTopWidth),
        linkBorderStyle: linkStyle.borderTopStyle,
        linkDecoration: linkStyle.textDecorationLine,
        badgeBorder: parseFloat(badgeStyle.borderTopWidth),
        badgeBorderStyle: badgeStyle.borderTopStyle,
        scrollWidth: document.documentElement.scrollWidth,
        viewportWidth: document.documentElement.clientWidth
      };
    });
    equal(highContrast.linkBorder >= 2 && highContrast.linkBorderStyle === 'solid', true,
      'live action remains bounded without forced background colors: ' + JSON.stringify(highContrast));
    equal(highContrast.linkDecoration.includes('underline'), true,
      'live action retains non-color link affordance');
    equal(highContrast.badgeBorder >= 1 && highContrast.badgeBorderStyle === 'solid', true,
      'availability badge remains bounded without its background color');
    equal(highContrast.scrollWidth <= highContrast.viewportWidth, true,
      'forced colors and enlarged text retain 320px reflow');
    await page.locator('#tool-query').fill('text lens');
    equal(await page.locator('.ft15-card h3').allTextContents(), ['Text Lens'],
      'search still operates in forced-colors mode');
    await page.locator('#tool-clear').click();
    equal(await page.locator('.ft15-card').count(), TOOLS.length,
      'clear still operates in forced-colors mode');
  }
  // WCAG 2.2 2.4.7/2.4.11: actual keyboard Tab traversal at narrow width
  // and 400% root-text scaling. Chromium additionally retains forced colors.
  // This checks rendered focus and viewport intersection, not screen readers,
  // native browser zoom, or a WCAG conformance certification.
  await page.locator('#tool-query').focus();
  for (const selector of ['#tool-category', '#tool-status', '#tool-clear', '.ft15-link']) {
    await page.keyboard.press('Tab');
    const focus = await page.evaluate(selector => {
      const el = document.activeElement;
      const style = getComputedStyle(el);
      const box = el.getBoundingClientRect();
      return {
        expected: el.matches(selector),
        outlineWidth: parseFloat(style.outlineWidth),
        outlineStyle: style.outlineStyle,
        intersectsViewport: box.width > 0 && box.height > 0 &&
          box.right > 0 && box.left < innerWidth &&
          box.bottom > 0 && box.top < innerHeight,
        horizontalOverflow: document.documentElement.scrollWidth >
          document.documentElement.clientWidth
      };
    }, selector);
    equal(focus.expected, true, 'Tab reaches ' + selector + ': ' + JSON.stringify(focus));
    equal(focus.outlineWidth >= 3 && focus.outlineStyle === 'solid', true,
      'visible keyboard outline on ' + selector + ': ' + JSON.stringify(focus));
    equal(focus.intersectsViewport && !focus.horizontalOverflow, true,
      'keyboard target remains visible without horizontal overflow: ' + selector + ' ' + JSON.stringify(focus));
  }
  await page.keyboard.press('Shift+Tab');
  equal(await page.locator('#tool-clear').evaluate(el => el === document.activeElement),
    true, 'reverse keyboard traversal returns to Clear filters');
  equal(errors, [], 'no runtime script errors');
  console.log('FT-15 ' + browserName + ' HTTP browser integration: ' + checks + '/' + checks + ' PASS');
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
