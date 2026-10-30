/**
 * FT-16: HTTP-served forced-colors accessibility acceptance, using only the
 * public catalog and synthetic search terms. Playwright emulates the CSS media
 * preference; this is NOT physical Windows High Contrast, screen-reader, or
 * full WCAG conformance testing.
 * Sources reviewed 2026-10-30:
 * https://playwright.dev/docs/emulation#emulate-media
 * https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/forced-colors
 * https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast
 */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium,firefox,webkit} from 'playwright';

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
let browser,checks=0;
function eq(actual,expected,label){assert.deepEqual(actual,expected,label);checks++;}
try{
 browser=await engine.launch({headless:true});
 const context=await browser.newContext({forcedColors:'active',viewport:{width:320,height:720}});
 const page=await context.newPage();
 const errors=[],external=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('request',request=>{
  if(!request.url().startsWith('http://127.0.0.1:'+server.address().port+'/'))
   external.push(request.url());
 });
 const response=await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'networkidle'});
 eq(response.status(),200,'HTTP fixture loaded');
 eq(await page.evaluate(()=>matchMedia('(forced-colors: active)').matches),true,
  'forced-colors preference actually active in browser');
 eq(await page.locator('.ft15-card').count(),17,'complete catalog available');
 eq(await page.locator('.ft15-link').count(),6,'approved live links remain available');
 eq(await page.locator('fieldset').isEnabled(),true,'search controls initialized');
 const styles=await page.evaluate(()=>{
  const style=selector=>getComputedStyle(document.querySelector(selector));
  return {
   cardBorder:style('.ft15-card').borderLeftWidth,
   badgeBorder:style('.ft15-badge').borderLeftWidth,
   linkBorder:style('.ft15-link').borderLeftWidth,
   linkBorderStyle:style('.ft15-link').borderLeftStyle,
   cardShadow:style('.ft15-card').boxShadow,
   linkTextDecoration:style('.ft15-link').textDecorationLine,
   forcedAdjust:style('.ft15-link').forcedColorAdjust
  };
 });
 eq(styles.cardBorder,'1px','cards retain visible structural borders');
 eq(styles.badgeBorder,'1px','status badges retain visible structural borders');
 eq(styles.linkBorder,'2px','live links retain explicit two-pixel boundaries');
 eq(styles.linkBorderStyle,'solid','link boundary is not hidden or dashed');
 eq(styles.cardShadow,'none','browser removes decorative shadow in forced colors');
 eq(styles.linkTextDecoration.includes('underline'),true,'links retain non-color affordance');
 eq(styles.forcedAdjust,'auto','do not opt out of user-forced palette');
 for(const selector of ['#tool-query','#tool-category','#tool-clear','.ft15-link']){
  await page.locator(selector).first().focus();
  const focus=await page.locator(selector).first().evaluate(el=>{
   const s=getComputedStyle(el);
   return {active:document.activeElement===el,style:s.outlineStyle,width:s.outlineWidth};
  });
  eq(focus.active,true,selector+' can receive focus');
  eq(focus.style,'solid',selector+' has a solid focus indicator');
  eq(focus.width,'3px',selector+' retains three-pixel focus outline');
 }
 await page.locator('#tool-query').fill('text\u202e lens');
 eq(await page.locator('#tool-query').getAttribute('aria-invalid'),'true',
  'unsafe pasted Unicode retains accessible error in forced colors');
 eq(await page.locator('#tool-query-error').isVisible(),true,
  'error text remains visible in forced colors');
 eq(await page.locator('.ft15-card').count(),0,'invalid search does not show misleading results');
 await page.locator('#tool-clear').click();
 eq(await page.locator('#tool-query').inputValue(),'','clear recovers from invalid query');
 eq(await page.locator('.ft15-card').count(),17,'clear restores all catalog entries');
 eq(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),
  true,'320 CSS-pixel viewport has no horizontal overflow in forced colors');
 // Negative control: removing the explicit forced-colors CSS must remove the
 // link boundary, proving the assertion above exercised the intended rule.
 const removed=await page.evaluate(()=>{
  const sheet=[...document.styleSheets].find(s=>s.href?.endsWith('/styles.css'));
  if(!sheet)throw Error('Missing same-origin styles.css');
  const index=[...sheet.cssRules].findIndex(rule=>rule.type===CSSRule.MEDIA_RULE&&
   /forced-colors\s*:\s*active/.test(rule.conditionText||''));
  if(index<0)throw Error('Missing forced-colors media rule');
  sheet.deleteRule(index);
  return {link:getComputedStyle(document.querySelector('.ft15-link')).borderLeftWidth,
   badge:getComputedStyle(document.querySelector('.ft15-badge')).borderLeftWidth};
 });
 eq(removed.link,'0px','negative control detects loss of explicit link border');
 eq(removed.badge,'0px','negative control detects loss of status badge border');
 eq(errors,[],'no application JavaScript errors');
 eq(external,[],'no off-origin requests or query transmission');
 console.log('FT-16 '+name+' forced-colors: '+checks+'/'+checks+' PASS (emulation, not physical OS mode)');
 await context.close();
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
