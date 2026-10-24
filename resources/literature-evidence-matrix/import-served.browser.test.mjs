import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium, firefox, webkit} from 'playwright';
import {SCHEMA} from './core.mjs';

// Only synthetic data enters the test. No documents or source text are uploaded.
const browserName=process.argv[2]||'chromium';
const engine={chromium,firefox,webkit}[browserName];
if(!engine)throw Error('Unknown browser engine');
const dir=dirname(fileURLToPath(import.meta.url));
const allowed=new Set(['index.html','app.mjs','core.mjs']);
const csp="default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'";
const server=createServer(async(req,res)=>{
 const path=new URL(req.url,'http://localhost').pathname;
 const name=path==='/'?'index.html':path.slice(1);
 if(!allowed.has(name)){res.writeHead(404);res.end('Not found');return}
 try{
  const body=await readFile(join(dir,name));
  res.writeHead(200,{'Content-Type':name.endsWith('.html')?'text/html; charset=utf-8':'text/javascript; charset=utf-8','Content-Security-Policy':csp,'X-Content-Type-Options':'nosniff'});
  res.end(body);
 }catch{res.writeHead(500);res.end('Unable to load')}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser,checks=0;
function check(actual,expected,message){assert.deepEqual(actual,expected,message);checks++}
function fixture(ids){return Buffer.from(JSON.stringify({schema:SCHEMA,sources:ids.map(id=>({id,title:'Synthetic '+id,year:null,doi:''})),claims:[]}),'utf8')}
async function upload(page,name,buffer){await page.locator('#upload').setInputFiles({name,mimeType:'application/json',buffer})}
try{
 browser=await engine.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:800},acceptDownloads:true});
 const errors=[],outbound=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('request',req=>{if(!req.url().startsWith('http://127.0.0.1:'+server.address().port+'/')&&!req.url().startsWith('blob:'))outbound.push(req.url())});
 const response=await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'networkidle'});
 check(response.status(),200,'HTML served over HTTP');
 check(response.headers()['content-security-policy'],csp,'enforced CSP header');
 check(await page.title(),'Literature Evidence Matrix','title');
 check(await page.locator('main').count(),1,'main landmark');
 check(await page.locator('#error[role="alert"][tabindex="-1"]').count(),1,'focusable error');
 check(await page.locator('#status[role="status"][aria-live="polite"]').count(),1,'status announcement');
 check(await page.locator('#upload[aria-describedby="import-help"]').count(),1,'file help associated');
 check(await page.locator('#import-preview').isHidden(),true,'no pending replacement initially');
 await page.evaluate(()=>{const s=document.createElement('script');s.textContent='window.__ft14_inline_executed=true';document.head.append(s)});
 check(await page.evaluate(()=>Boolean(window.__ft14_inline_executed)),false,'CSP blocks inline execution');

 await page.locator('#source input[name="id"]').fill('0007');
 await page.locator('#source input[name="title"]').fill('<img src=x onerror=alert(1)>');
 await page.locator('#source button').click();
 check(await page.locator('#counts').textContent(),'1 sources, 0 findings, 1 gaps, 0 tensions.','original source added');
 check(await page.locator('#sources li').count(),1,'one source visible');
 check(await page.locator('#sources img').count(),0,'hostile title rendered as text');
 check((await page.locator('#sources li').textContent()).includes('<img src=x onerror=alert(1)>'),true,'literal title preserved');

 await upload(page,'broken.json',Buffer.from('{"schema":','utf8'));
 await page.waitForFunction(()=>document.querySelector('#error').textContent.includes('Invalid JSON'));
 check(await page.locator('#error').evaluate(el=>el===document.activeElement),true,'invalid file error receives focus');
 check(await page.locator('#counts').textContent(),'1 sources, 0 findings, 1 gaps, 0 tensions.','invalid file preserves matrix');
 check(await page.locator('#import-preview').isHidden(),true,'invalid file has no preview');

 await upload(page,'candidate.JSON',fixture(['0010','β-0020']));
 await page.locator('#import-preview').waitFor({state:'visible'});
 check(await page.locator('#error').textContent(),'','valid selection clears stale error');
 check(await page.locator('#confirm-import').evaluate(el=>el===document.activeElement),true,'preview confirmation receives focus');
 check((await page.locator('#import-summary').textContent()).includes('Replace the current 1 sources and 0 findings with 2 sources and 0 findings?'),true,'preview describes both record counts');
 check(await page.locator('#counts').textContent(),'1 sources, 0 findings, 1 gaps, 0 tensions.','preview does not replace data');
 await page.locator('#cancel-import').click();
 check(await page.locator('#import-preview').isHidden(),true,'cancel hides preview');
 check(await page.locator('#upload').evaluate(el=>el===document.activeElement),true,'cancel returns focus to file chooser');
 check((await page.locator('#sources li').textContent()).startsWith('0007 —'),true,'cancel preserves original ID');

 await upload(page,'candidate.json',fixture(['0010','β-0020']));
 await page.locator('#import-preview').waitFor({state:'visible'});
 await page.locator('#confirm-import').click();
 check(await page.locator('#counts').textContent(),'2 sources, 0 findings, 2 gaps, 0 tensions.','confirmed replacement updates count');
 check(await page.locator('#import-preview').isHidden(),true,'confirmation closes preview');
 check(await page.locator('#sources li').allTextContents(),['0010 — Synthetic 0010','β-0020 — Synthetic β-0020'],'exact zero-padded and Unicode IDs retained');
 check((await page.locator('#status').textContent()).includes('confirmed'),true,'confirmation status');

 const downloadPromise=page.waitForEvent('download');
 await page.locator('#download').click();
 const download=await downloadPromise;
 check(download.suggestedFilename(),'literature-evidence-matrix.json','local download filename');
 const saved=JSON.parse(await readFile(await download.path(),'utf8'));
 check(saved.sources.map(x=>x.id),['0010','β-0020'],'download preserves exact IDs');
 check(saved.schema,SCHEMA,'download schema');
 await upload(page,'oversized.json',Buffer.alloc(2000001,0x20));
 await page.waitForFunction(()=>document.querySelector('#error').textContent.includes('up to 2 MB'));
 check(await page.locator('#import-preview').isHidden(),true,'oversized file cannot replace data');
 check(await page.locator('#counts').textContent(),'2 sources, 0 findings, 2 gaps, 0 tensions.','oversized file leaves data intact');

 await page.setViewportSize({width:320,height:720});
 check(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),true,'320px responsive reflow');
 await page.evaluate(()=>{document.documentElement.style.fontSize='200%'});
 check(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),true,'200% root text reflow (not native zoom)');
 check(await page.locator('#upload').isVisible(),true,'file chooser remains available at narrow width');
 check(errors,[],'no page script errors');
 check(outbound,[],'no outbound network requests');
 console.log('FT-14 '+browserName+' HTTP/CSP import acceptance: '+checks+'/'+checks+' PASS');
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
