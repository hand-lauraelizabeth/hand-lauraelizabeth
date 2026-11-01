/**
 * FT-16: HTTP/CSP browser regression for input-method editor (IME) composition.
 * Synthetic event sequences are NOT a native keyboard/IME accessibility audit.
 * W3C Input Events Level 2: https://www.w3.org/TR/input-events-2/
 * W3C WCAG 2.2 Error Identification: https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html
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
  if(negative&&file==='app.mjs'){
   const anchor='if(composing)return;';
   assert.ok(data.includes(anchor),'negative control must mutate composition guard');
   data=data.replace(anchor,'if(false)return;');
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
 eq(response.headers()['content-security-policy'],csp,'CSP enforced');
 eq(await page.locator('.ft15-card').count(),17,'catalog initially visible');
 eq(await page.locator('#tool-query').isEnabled(),true,'input ready');
 // Simulate an IME's intermediate invalid UTF-16 value and input event.
 await page.evaluate(()=>{
  const input=document.getElementById('tool-query');
  input.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true,data:''}));
  input.value='text\uD800';
  input.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:true,
   inputType:'insertCompositionText',data:'x'}));
 });
 eq(await page.locator('#tool-query').inputValue(),'text\uD800','intermediate IME text stays editable');
 eq(await page.locator('.ft15-card').count(),17,'composition does not prematurely replace results');
 eq(await page.locator('#tool-query-error').isHidden(),true,'no transient invalid-Unicode alert');
 eq(await page.locator('#tool-query').getAttribute('aria-invalid'),null,'no premature invalid state');
 // Changing a separate filter during composition must also defer announcements.
 await page.locator('#tool-status').selectOption('live');
 eq(await page.locator('.ft15-card').count(),17,'filter change waits for composition to finish');
 eq(await page.locator('#tool-count').textContent(),'17 of 17 resources shown','status not announced prematurely');
 await page.evaluate(()=>{
  const input=document.getElementById('tool-query');
  input.value='text lens';
  input.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true,data:'text lens'}));
 });
 eq(await page.locator('.ft15-card h3').allTextContents(),['Text Lens'],'committed IME value and pending filter applied');
 eq(await page.locator('#tool-query-error').isHidden(),true,'committed valid query has no alert');
 eq(await page.locator('#tool-count').textContent(),'1 of 17 resources shown','one final status announcement');
 // Committed unsafe text must still be rejected, not silently normalized.
 await page.evaluate(()=>{
  const input=document.getElementById('tool-query');
  input.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));
  input.value='text\u202e lens';
  input.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:true,
   inputType:'insertCompositionText',data:'x'}));
 });
 await page.locator('#tool-status').selectOption('development');
 eq(await page.locator('.ft15-card h3').allTextContents(),['Text Lens'],'second composition preserves previous cards');
 eq(await page.locator('#tool-query-error').isHidden(),true,'second composition has no transient alert');
 await page.locator('#tool-query').evaluate(input=>
  input.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true,data:'text\u202e lens'})));
 eq(await page.locator('#tool-query-error').isVisible(),true,'committed control character shows error');
 eq(await page.locator('#tool-query').getAttribute('aria-invalid'),'true','committed unsafe query marked invalid');
 eq(await page.locator('.ft15-card').count(),0,'committed unsafe query has no partial matches');
 await page.locator('#tool-clear').click();
 eq(await page.locator('.ft15-card').count(),17,'clear restores catalog after unsafe commit');
 eq(await page.locator('#tool-query').evaluate(el=>el===document.activeElement),true,'clear restores focus');
 // Cancellation restores the original search rather than an obsolete alert.
 await page.locator('#tool-query').fill('text lens');
 await page.evaluate(()=>{
  const input=document.getElementById('tool-query');
  input.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));
  input.value='x\uD800';
  input.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:true,
   inputType:'insertCompositionText',data:'x'}));
  input.value='text lens';
  input.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true,data:''}));
 });
 eq(await page.locator('.ft15-card h3').allTextContents(),['Text Lens'],'canceled composition restores search');
 eq(await page.locator('#tool-query-error').isHidden(),true,'cancel does not leave stale error');
 eq(await page.locator('#tool-query').getAttribute('aria-invalid'),null,'cancel leaves valid input');
 eq(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),
  true,'320 CSS-pixel layout does not overflow');
 eq(errors,[],'no page errors');
 eq(external,[],'no off-origin requests');
 console.log('FT-16 '+name+' IME composition '+checks+'/'+checks+' PASS'+(negative?' NEGATIVE':''));
 await context.close();
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
