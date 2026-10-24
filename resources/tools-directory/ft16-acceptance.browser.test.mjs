/**
 * FT-16: public-safe synthetic acceptance test for the real HTTP-served directory.
 * The catalog fixture replaces only the response to /catalog.mjs; the HTML, styles,
 * directory validator and app modules are read unchanged from this repository.
 * A deliberately unsafe app mutation is available ONLY as a test negative control.
 */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium, firefox, webkit } from 'playwright';
import { validateCatalog } from './directory.mjs';

const browserName = process.argv[2] || 'chromium';
const negativeControl = process.argv.includes('--negative-control');
const engine = { chromium, firefox, webkit }[browserName];
if (!engine) throw Error('Unsupported browser: ' + browserName);
const dir = dirname(fileURLToPath(import.meta.url));
const payloads = [
  '<img src=x onerror="window.__ft16_executed=1">',
  '<svg onload="window.__ft16_executed=1"></svg>',
  '<script>window.__ft16_executed=1</script>'
];
const rows = [
  { id:'safe', title:'Safe resource', category:'Research', status:'live',
    description:'A benign synthetic entry', url:'https://www.lauraelizabethhand.com/resources/example/' },
  ...payloads.map((value,i) => ({
    id:'fixture-'+i, title:value, category:'Untrusted metadata',
    status:'development', description:'Description: '+value
  }))
];
let checks = 0;
function eq(actual, expected, message) { assert.deepEqual(actual, expected, message); checks++; }
function rejected(rowsToCheck, message) { assert.throws(() => validateCatalog(rowsToCheck), message); checks++; }
eq(validateCatalog(rows), true, 'valid synthetic catalog');
for (const badUrl of [
  'javascript:alert(1)', 'http://www.lauraelizabethhand.com/resources/example/',
  'https://www.lauraelizabethhand.com.evil.invalid/resources/example/',
  'https://www.lauraelizabethhand.com/other/example/',
  'https://user:pass@www.lauraelizabethhand.com/resources/example/',
  'https://www.lauraelizabethhand.com/resources/example/?leak=1',
  'https://www.lauraelizabethhand.com/resources/example/#leak'
]) rejected([{...rows[0],url:badUrl}], 'unsafe destination '+badUrl);
rejected([{...rows[1],url:'https://www.lauraelizabethhand.com/resources/example/'}], 'unreleased item linked');
rejected([rows[0], {...rows[0]}], 'duplicate IDs');
rejected([{...rows[0],id:'bad id'}], 'invalid ID');
rejected([{...rows[0],description:''}], 'missing description');
rejected([{...rows[0],status:'unknown'}], 'unknown availability');

const allowed = new Set(['index.html','app.mjs','catalog.mjs','directory.mjs',
  'styles.css','layout.css','controls.css','focus.css']);
const types = { html:'text/html; charset=utf-8', mjs:'text/javascript; charset=utf-8',
  css:'text/css; charset=utf-8' };
// Match a locked-down deployment: same-origin modules/styles, no inline scripts or network connections.
// W3C CSP3: https://www.w3.org/TR/CSP/ (checked 2026-10-24).
const csp = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'";
const fixtureCatalog = 'export const TOOLS = Object.freeze('+JSON.stringify(rows)+');\n'
  + 'export const STATUS_LABELS = Object.freeze({live:"Live",preview:"Preview",development:"In development"});\n';
const server = createServer(async (req,res) => {
  const name = new URL(req.url,'http://localhost').pathname.slice(1) || 'index.html';
  if (!allowed.has(name)) { res.writeHead(404); res.end('Not found'); return; }
  try {
    let data = name === 'catalog.mjs' ? fixtureCatalog : await readFile(join(dir,name),'utf8');
    if (negativeControl && name === 'app.mjs') {
      const original = 'if(text!==undefined)e.textContent=text;return e;';
      assert.ok(data.includes(original), 'negative control must alter exact current sink');
      data = data.replace(original, 'if(text!==undefined)e.innerHTML=text;return e;');
    }
    res.writeHead(200, {'Content-Type':types[name.split('.').at(-1)],
      'X-Content-Type-Options':'nosniff', 'Content-Security-Policy':csp});
    res.end(data);
  } catch (error) { res.writeHead(500); res.end('Fixture failure'); }
});
await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
let browser;
try {
  browser = await engine.launch({headless:true});
  const page = await browser.newPage({viewport:{width:1280,height:800}});
  const pageErrors = [], externalRequests = [];
  page.on('pageerror',error=>pageErrors.push(error.message));
  page.on('request',request=>{
    if (!request.url().startsWith('http://127.0.0.1:'+server.address().port+'/'))
      externalRequests.push(request.url());
  });
  const response = await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'networkidle'});
  eq(response.status(),200,'real HTTP-served app');
  eq(response.headers()['content-security-policy'],csp,'enforced HTTP Content-Security-Policy header');
  await page.locator('.ft15-card').first().waitFor();
  eq(await page.locator('.ft15-card').count(),4,'all synthetic records');
  eq(await page.locator('.ft15-card h3').allTextContents(),rows.map(r=>r.title),'literal exact headings');
  eq(await page.locator('.ft15-card p:not(.ft15-unavailable)').allTextContents(),
    rows.map(r=>r.description),'literal exact descriptions');
  eq(await page.locator('.ft15-card img,.ft15-card svg,.ft15-card script').count(),
    0,'untrusted metadata never parsed into DOM elements');
  eq(await page.evaluate(()=>window.__ft16_executed===undefined),true,'no untrusted script executed');
  // Prove the browser enforces the policy, rather than merely asserting header text.
  await page.evaluate(() => {
    window.__ft16_violations = [];
    document.addEventListener('securitypolicyviolation', event => {
      window.__ft16_violations.push(event.violatedDirective);
    });
    const inline = document.createElement('script');
    inline.textContent = 'window.__ft16_inline_executed=true';
    document.body.append(inline);
    inline.remove();
    const trigger = document.createElement('button');
    trigger.setAttribute('onclick','window.__ft16_handler_executed=true');
    document.body.append(trigger);
    trigger.click();
    trigger.remove();
  });
  await page.waitForTimeout(50);
  eq(await page.evaluate(()=>window.__ft16_inline_executed===undefined),true,
    'CSP blocks injected inline script');
  eq(await page.evaluate(()=>window.__ft16_handler_executed===undefined),true,
    'CSP blocks injected inline event handler');
  eq(await page.evaluate(()=>window.__ft16_violations.filter(x=>x.startsWith('script-src')).length>=2),
    true,'browser emitted script-src policy violations for both probes');
  eq(await page.locator('.ft15-link').count(),1,'only approved live entry linked');
  eq(await page.locator('.ft15-link').getAttribute('href'),rows[0].url,'exact approved href');
  eq(await page.locator('.ft15-unavailable').count(),3,'development entries unavailable');
  eq(await page.locator('#tool-count[role="status"][aria-atomic="true"]').count(),1,'accessible count');
  eq(await page.locator('#tool-count').textContent(),'4 of 4 resources shown','initial count');
  eq(pageErrors,[],'no application JavaScript errors');
  eq(externalRequests,[],'no outbound requests');
  await page.locator('#tool-query').fill('fixture');
  eq(await page.locator('.ft15-card').count(),0,'private fixture IDs not searchable');
  await page.locator('#tool-query').fill('<script>');
  eq(await page.locator('.ft15-card').count(),1,'literal markup text searchable');
  await page.locator('#tool-status').selectOption('development');
  eq(await page.locator('.ft15-card').count(),1,'combined filter');
  await page.locator('#tool-query').fill('');
  eq(await page.locator('.ft15-card').count(),3,'development filter');
  await page.locator('#tool-clear').focus();
  await page.keyboard.press('Enter');
  eq(await page.locator('.ft15-card').count(),4,'keyboard clear restores records');
  eq(await page.locator('#tool-query').evaluate(el=>el===document.activeElement),
    true,'keyboard clear returns focus to search');
  await page.setViewportSize({width:320,height:720});
  eq(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),
    true,'320 CSS-pixel reflow');
  await page.evaluate(()=>{document.documentElement.style.fontSize='200%';});
  eq(await page.evaluate(()=>parseFloat(getComputedStyle(document.documentElement).fontSize)>=30),
    true,'200% root-text setting actually applied before reflow assertion');
  eq(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),
    true,'200% root-text reflow; not native browser zoom');
  eq(pageErrors,[],'no runtime JavaScript errors');
  eq(externalRequests,[],'no outbound requests after interactions');
  console.log('FT-16 '+browserName+' '+(negativeControl?'NEGATIVE CONTROL ':'')+checks+'/'+checks+' PASS');
} finally {
  if (browser) await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
