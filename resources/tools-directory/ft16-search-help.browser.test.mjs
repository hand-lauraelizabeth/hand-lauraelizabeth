/**
 * FT-16: Search-field instructions and recoverable error descriptions.
 * Real HTTP-served, CSP-restricted browser checks use public catalog and
 * synthetic inputs only. Negative control deliberately breaks the help ID.
 * Sources reviewed 2026-10-30:
 * https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html
 * https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html
 * https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html
 * These tests do not substitute for native screen-reader or actual zoom review.
 */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium,firefox,webkit} from 'playwright';

const name=process.argv[2]||'chromium';
const negative=process.argv.includes('--negative-control');
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
  let data=await readFile(join(dir,file),'utf8');
  if(negative&&file==='index.html'){
   const anchor='id="tool-search-help"';
   assert.ok(data.includes(anchor),'negative control must mutate current help');
   data=data.replace(anchor,'id="tool-search-help-removed"');
  }
  const type=file.endsWith('.html')?'text/html':file.endsWith('.css')?'text/css':'text/javascript';
  res.writeHead(200,{'Content-Type':type+'; charset=utf-8',
   'X-Content-Type-Options':'nosniff','Content-Security-Policy':csp});
  res.end(data);
 }catch{res.writeHead(500);res.end('Fixture failure');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser,checks=0;
function eq(actual,expected,label){assert.deepEqual(actual,expected,label);checks++;}
try{
 browser=await engine.launch({headless:true});
 const context=await browser.newContext({viewport:{width:320,height:720}});
 const page=await context.newPage();
 const errors=[],external=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('request',request=>{
  if(!request.url().startsWith('http://127.0.0.1:'+server.address().port+'/'))
   external.push(request.url());
 });
 const response=await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'networkidle'});
 eq(response.status(),200,'HTTP page served');
 eq(response.headers()['content-security-policy'],csp,'CSP enforced as HTTP header');
 eq(await page.locator('#tool-query').isEnabled(),true,'search initialized');
 eq(await page.locator('.ft15-card').count(),17,'public catalog loaded');
 const description=()=>page.locator('#tool-query').evaluate(el=>{
  const ids=(el.getAttribute('aria-describedby')||'').split(/\s+/).filter(Boolean);
  return {ids,texts:ids.map(id=>document.getElementById(id)?.textContent||null),
   visible:ids.map(id=>!!document.getElementById(id)?.getClientRects().length)};
 });
 let state=await description();
 eq(state.ids,['tool-search-help'],'normal state retains the help relationship');
 eq(state.texts.length,1,'one persistent description');
 eq(state.texts[0]?.includes('256 Unicode code points'),true,'help states exact limit');
 eq(state.texts[0]?.includes('Searches stay in your browser'),true,'help explains local privacy');
 eq(state.visible,[true],'instructions are visible, not screen-reader-only');
 eq(await page.locator('#tool-query').getAttribute('aria-invalid'),null,'normal input valid');
 await page.locator('#tool-query').fill('a'.repeat(257));
 state=await description();
 eq(state.ids,['tool-search-help','tool-query-error'],'overlength error adds to help');
 eq(state.visible,[true,true],'help and overlength error remain visible');
 eq(state.texts[1]?.includes('Shorten your query'),true,'overlength text gives correction');
 eq(await page.locator('#tool-query').getAttribute('aria-invalid'),'true','overlength marked invalid');
 eq(await page.locator('.ft15-card').count(),0,'invalid query does not show results');
 await page.locator('#tool-query').fill('🎓'+String.fromCodePoint(0x202e)+' research');
 state=await description();
 eq(state.ids,['tool-search-help','tool-query-error'],'Unicode error preserves help');
 eq(state.texts[1]?.includes('U+202E'),true,'error identifies Unicode code point');
 eq(state.texts[1]?.includes('position 2'),true,'supplementary emoji counts as one point');
 eq(await page.locator('#tool-query').getAttribute('aria-invalid'),'true','Unicode marked invalid');
 await page.locator('#tool-query').fill('research');
 state=await description();
 eq(state.ids,['tool-search-help'],'correction removes only error relationship');
 eq(await page.locator('#tool-query-error').isVisible(),false,'resolved error hidden');
 eq(await page.locator('#tool-query').getAttribute('aria-invalid'),null,'correction clears invalid');
 eq(await page.locator('.ft15-card').count()>0,true,'search results recover');
 await page.locator('#tool-status').selectOption('development');
 eq((await description()).ids,['tool-search-help'],'filter changes preserve help');
 await page.locator('#tool-clear').click();
 eq((await description()).ids,['tool-search-help'],'clear preserves help');
 eq(await page.locator('#tool-query').inputValue(),'','clear empties query');
 eq(await page.locator('#tool-query').evaluate(el=>document.activeElement===el),true,
  'clear returns keyboard focus to search');
 eq(await page.locator('.ft15-card').count(),17,'clear restores all resources');
 await page.evaluate(()=>{document.documentElement.style.fontSize='400%';});
 eq(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),
  true,'320px 400% root text reflows (not native browser zoom)');
 eq(errors,[],'no JavaScript errors');
 eq(external,[],'no off-origin requests or query transmission');
 console.log('FT-16 '+name+' search-help '+checks+'/'+checks+' PASS'+(negative?' NEGATIVE':''));
 await context.close();
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
