/**
 * FT-15/FT-16: prove that an already-loaded directory continues to work
 * without network access, and that disabled JavaScript is explained rather
 * than leaving apparently functional, inert search controls.
 * Tests use only synthetic search terms and a loopback HTTP fixture.
 * WHATWG HTML noscript/fieldset and Playwright BrowserContext.setOffline,
 * reviewed 2026-10-30. This does not establish first-load offline support.
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
 const origin='http://127.0.0.1:'+server.address().port+'/';
 const context=await browser.newContext({viewport:{width:320,height:720}});
 const page=await context.newPage();
 const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const response=await page.goto(origin,{waitUntil:'networkidle'});
 eq(response.status(),200,'initial HTTP load');
 eq(await page.locator('fieldset').isEnabled(),true,'local initialization enables controls');
 eq(await page.locator('.ft15-card').count(),17,'initial catalog rendered');
 eq(await page.locator('#ft15-load-status').isHidden(),true,
  'successful initialization hides the fail-closed loading explanation');
 eq(await page.locator('noscript p').count(),0,'no-script explanation not rendered with scripting enabled');
 const requests=[];
 page.on('request',request=>requests.push(request.url()));
 await context.setOffline(true);
 await page.locator('#tool-query').fill('text lens');
 eq(await page.locator('.ft15-card h3').allTextContents(),['Text Lens'],
  'offline search remains functional after initial load');
 eq(await page.locator('#tool-count').textContent(),'1 of 17 resources shown',
  'offline status count remains accurate');
 await page.locator('#tool-status').selectOption('development');
 eq(await page.locator('.ft15-card').count(),0,'offline combined filter works');
 await page.locator('#tool-query').fill('x'.repeat(257));
 eq(await page.locator('#tool-query').getAttribute('aria-invalid'),'true',
  'offline overlong query receives accessible error');
 eq(await page.locator('#tool-query-error').isVisible(),true,
  'offline error message remains visible');
 await page.locator('#tool-query').fill('text\u202e lens');
 eq((await page.locator('#tool-query-error').textContent()).includes('U+202E'),true,
  'offline Unicode control diagnostic remains available');
 await page.locator('#tool-clear').click();
 eq(await page.locator('.ft15-card').count(),17,'offline clear restores catalog');
 eq(await page.locator('#tool-query').inputValue(),'','offline clear resets input');
 eq(await page.locator('#tool-query').evaluate(el=>el===document.activeElement),true,
  'offline clear returns keyboard focus');
 eq(requests,[],'offline interactions issue no network requests');
 eq(errors,[],'offline interactions cause no JavaScript errors');
 await context.close();

 const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:320,height:720}});
 const staticPage=await nojs.newPage();
 const staticResponse=await staticPage.goto(origin,{waitUntil:'load'});
 eq(staticResponse.status(),200,'no-script HTML loads');
 eq(await staticPage.locator('#ft15-no-script').isVisible(),true,
  'visible no-script explanation');
 eq(await staticPage.locator('#ft15-load-status').isVisible(),true,
  'initialization explanation remains visible when scripting is disabled');
 eq((await staticPage.locator('#ft15-no-script').textContent()).includes('Enable JavaScript and reload'),true,
  'no-script explanation provides a corrective action');
 eq(await staticPage.locator('#tool-query').isDisabled(),true,
  'search is not misleadingly operable without scripting');
 eq(await staticPage.locator('#tool-category').isDisabled(),true,
  'category is disabled without scripting');
 eq(await staticPage.locator('#tool-status').isDisabled(),true,
  'availability filter is disabled without scripting');
 eq(await staticPage.locator('#tool-clear').isDisabled(),true,
  'clear button is disabled without scripting');
 eq(await staticPage.locator('.ft15-card').count(),0,
  'no-script mode does not pretend to display a loaded catalog');
 eq(await staticPage.locator('main h1').textContent(),'Find a Tool',
  'no-script mode retains main landmark and heading');

 // Negative controls: scripting may be enabled but its module or dependency
 // can fail to load. In either case, the directory must not appear ready.
 for(const missingModule of ['app.mjs','catalog.mjs']){
  const failedContext=await browser.newContext({viewport:{width:320,height:720}});
  const failedPage=await failedContext.newPage();
  const intercepted=[];
  await failedPage.route('**/'+missingModule,route=>{
   intercepted.push(route.request().url());
   return route.abort('failed');
  });
  const failedResponse=await failedPage.goto(origin,{waitUntil:'load'});
  eq(failedResponse.status(),200,'HTML loads when '+missingModule+' is unavailable');
  eq(intercepted.length,1,missingModule+' failure was actually injected');
  eq(await failedPage.locator('#ft15-load-status').isVisible(),true,
   'load failure retains visible recovery instructions: '+missingModule);
  eq((await failedPage.locator('#ft15-load-status').textContent()).includes('reload'),true,
   'load failure gives actionable recovery: '+missingModule);
  eq(await failedPage.locator('#tool-query').isDisabled(),true,
   'search remains disabled when '+missingModule+' fails');
  eq(await failedPage.locator('#tool-clear').isDisabled(),true,
   'clear remains disabled when '+missingModule+' fails');
  eq(await failedPage.locator('.ft15-card').count(),0,
   'load failure does not misrepresent an empty catalog: '+missingModule);
  eq(await failedPage.locator('#ft15-no-script').count(),0,
   'no-script text is not falsely shown when scripts are enabled: '+missingModule);
  await failedContext.close();
 }
 console.log('FT-16 '+name+' offline/no-script: '+checks+'/'+checks+' PASS');
 await nojs.close();
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
