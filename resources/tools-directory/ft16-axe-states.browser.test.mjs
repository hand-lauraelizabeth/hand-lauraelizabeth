/**
 * FT-15/FT-16: automated accessibility checks of real, HTTP-served states.
 * Uses synthetic queries only; this is not native screen-reader or WCAG certification.
 * Official context: https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html
 * Deque axe API: https://www.deque.com/axe/core-documentation/api-documentation/
 * Reviewed 2026-10-30.
 */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium,firefox,webkit} from 'playwright';
import AxeBuilder from '@axe-core/playwright';

const name=process.argv[2]||'chromium';
const engine={chromium,firefox,webkit}[name];
if(!engine)throw Error('Unsupported browser '+name);
const dir=dirname(fileURLToPath(import.meta.url));
const allowed=new Set(['index.html','app.mjs','catalog.mjs','directory.mjs',
 'styles.css','layout.css','controls.css','focus.css']);
const csp="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'self' data:; font-src 'self'; object-src 'none'; form-action 'none'; base-uri 'none'";
const server=createServer(async(req,res)=>{
 const file=new URL(req.url,'http://localhost').pathname.slice(1)||'index.html';
 if(!allowed.has(file)){res.writeHead(404);res.end('Not found');return;}
 try{
  const type=file.endsWith('.html')?'text/html':file.endsWith('.css')?'text/css':'text/javascript';
  const data=await readFile(join(dir,file));
  res.writeHead(200,{'Content-Type':type+'; charset=utf-8',
   'X-Content-Type-Options':'nosniff','Content-Security-Policy':csp});
  res.end(data);
 }catch{res.writeHead(500);res.end('Fixture failure');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser;
let scans=0,assertions=0;
const tags=['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa'];
async function audit(page,label){
 const result=await new AxeBuilder({page}).withTags(tags).analyze();
 assert.ok(result.passes.length>=10,label+': axe must actually execute multiple rules');
 assertions++;
 const failures=result.violations.map(v=>({rule:v.id,impact:v.impact,
  nodes:v.nodes.map(n=>n.target.join(' '))}));
 assert.deepEqual(failures,[],label+': axe violations');
 assertions++;
 scans++;
 console.log('FT-16 axe '+name+' '+label+': '+result.passes.length+
  ' rules passed, '+result.violations.length+' violations, '+
  result.incomplete.length+' manual-review/incomplete rules');
}
try{
 browser=await engine.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1280,height:900}});
 const page=await context.newPage();
 const response=await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'networkidle'});
 assert.equal(response.status(),200,'HTTP fixture loaded');assertions++;
 await page.locator('.ft15-card').first().waitFor();
 await audit(page,'initial catalog');
 await page.locator('#tool-status').selectOption('development');
 await audit(page,'development-only');
 await page.locator('#tool-query').fill('synthetic-no-results-xyz987');
 await audit(page,'zero-results');
 await page.locator('#tool-query').fill('x'.repeat(257));
 assert.equal(await page.locator('#tool-query').getAttribute('aria-invalid'),'true');
 assertions++;
 await audit(page,'overlong-query error');
 await page.locator('#tool-query').fill('text\u202e lens');
 assert.equal(await page.locator('#tool-query').getAttribute('aria-invalid'),'true');
 assertions++;
 await audit(page,'direction-control error');
 await page.locator('#tool-clear').click();
 await page.setViewportSize({width:320,height:720});
 await page.evaluate(()=>{document.documentElement.style.fontSize='400%';});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),true);
 assertions++;
 await audit(page,'320px viewport / 400% root text (not browser zoom)');
 // Negative control proves this is an active audit, not a vacuous no-violation check.
 await page.evaluate(()=>{
  const input=document.getElementById('tool-query');
  input.closest('label').replaceWith(input);
  input.removeAttribute('placeholder'); // placeholder can be treated as a fallback name
 });
 const negative=await new AxeBuilder({page}).withRules(['label']).analyze();
 assert.ok(negative.violations.some(v=>v.id==='label'&&
  v.nodes.some(n=>n.target.some(selector=>selector.includes('#tool-query')))),
  'negative control must detect intentionally unlabeled search input');
 assertions++;
 console.log('FT-16 axe '+name+' NEGATIVE CONTROL: unlabeled search detected');
 console.log('FT-16 axe '+name+': '+scans+' states; '+assertions+'/'+assertions+' assertions PASS');
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
