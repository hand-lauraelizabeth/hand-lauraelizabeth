/**
 * FT-16: fail-closed release links, including an app-layer defense-in-depth check.
 * The browser fixture deliberately bypasses catalog validation ONLY in this test,
 * so a synthetic preview URL cannot silently become a public link if a future
 * integration omits the validation call. No production destination is contacted.
 * Sources reviewed 2026-10-30:
 * https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html
 * https://html.spec.whatwg.org/multipage/links.html
 */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium,firefox,webkit} from 'playwright';
import {validateCatalog} from './directory.mjs';

const browserName=process.argv[2]||'chromium';
const negative=process.argv.includes('--negative-control');
const engine={chromium,firefox,webkit}[browserName];
if(!engine)throw Error('Unsupported browser '+browserName);
const dir=dirname(fileURLToPath(import.meta.url));
const url='https://www.lauraelizabethhand.com/resources/synthetic-tool/';
const live={id:'synthetic-live',title:'Synthetic live tool',category:'Research',description:'Synthetic live resource',status:'live',url};
const preview={id:'synthetic-preview',title:'Synthetic preview tool',category:'Research',description:'Not publicly available',status:'preview'};
const development={id:'synthetic-development',title:'Synthetic development tool',category:'Research',description:'Planned only',status:'development'};
let checks=0;
function eq(actual,expected,label){assert.deepEqual(actual,expected,label);checks++;}
eq(validateCatalog([live,preview,development]),true,'preview without URL is valid metadata');
for(const entry of [preview,development]){
 assert.throws(()=>validateCatalog([{...entry,url}]),/Unreleased tool cannot have a link/,
  'unreleased '+entry.status+' URL rejected by validator');checks++;
}
eq(validateCatalog([live]),true,'live approved URL remains valid');
const fixture=[live,{...preview,url},development];
const allowed=new Set(['index.html','app.mjs','catalog.mjs','directory.mjs','styles.css','layout.css','controls.css','focus.css']);
const csp="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'self' data:; font-src 'self'; object-src 'none'; form-action 'none'; base-uri 'none'";
const server=createServer(async(req,res)=>{
 const name=new URL(req.url,'http://localhost').pathname.slice(1)||'index.html';
 if(!allowed.has(name)){res.writeHead(404);res.end('Not found');return;}
 try{
  let source=name==='catalog.mjs'
   ? 'export const TOOLS='+JSON.stringify(fixture)+';\\nexport const STATUS_LABELS={live:"Live",preview:"Preview",development:"In development"};\\n'
   : await readFile(join(dir,name),'utf8');
  if(name==='directory.mjs'){
   const guard='validateCatalog();';
   assert.ok(source.includes(guard),'fixture must target actual validation call');
   source=source.replace(guard,'/* Synthetic test only: bypass catalog validation to exercise app-layer release gate. */');
  }
  if(negative&&name==='app.mjs'){
   const guard="if(tool.status==='live' && tool.url){";
   assert.ok(source.includes(guard),'negative control must alter exact live-only guard');
   source=source.replace(guard,'if(tool.url){');
  }
  const type=name.endsWith('.html')?'text/html':name.endsWith('.css')?'text/css':'text/javascript';
  res.writeHead(200,{'Content-Type':type+'; charset=utf-8',
   'X-Content-Type-Options':'nosniff','Content-Security-Policy':csp});
  res.end(source);
 }catch(err){res.writeHead(500);res.end('Fixture error: '+err.message);}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser;
try{
 browser=await engine.launch({headless:true});
 const page=await browser.newPage({viewport:{width:320,height:720}});
 const errors=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(!r.url().startsWith('http://127.0.0.1:'+server.address().port+'/'))external.push(r.url());});
 const response=await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'networkidle'});
 eq(response.status(),200,'HTTP-served app');
 eq(response.headers()['content-security-policy'],csp,'enforced CSP');
 eq(await page.locator('#tool-query').isEnabled(),true,'directory initialized');
 eq(await page.locator('.ft15-card').count(),3,'all synthetic availability states visible');
 eq(await page.locator('.ft15-link').count(),1,'only explicitly live entry is navigable');
 eq(await page.locator('.ft15-link').getAttribute('href'),url,'live destination unchanged');
 eq(await page.locator('.ft15-link').getAttribute('rel'),'noreferrer','live link suppresses referrer');
 eq(await page.locator('.ft15-unavailable').count(),2,'preview and development both unavailable');
 eq(await page.locator('.ft15-badge').allTextContents(),['Live','Preview','In development'],'statuses remain accurately labeled');
 await page.locator('#tool-status').selectOption('preview');
 eq(await page.locator('.ft15-card h3').allTextContents(),[preview.title],'preview filter works');
 eq(await page.locator('.ft15-link').count(),0,'preview filter exposes no link');
 eq(await page.locator('.ft15-unavailable').count(),1,'preview has explicit unavailable notice');
 await page.locator('#tool-status').selectOption('development');
 eq(await page.locator('.ft15-link').count(),0,'development filter exposes no link');
 await page.locator('#tool-status').selectOption('live');
 eq(await page.locator('.ft15-link').count(),1,'live filter preserves approved link');
 await page.locator('#tool-clear').click();
 eq(await page.locator('.ft15-link').count(),1,'clearing filters does not release preview URL');
 eq(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),true,'320px reflow');
 eq(errors,[],'no browser script errors');
 eq(external,[],'no off-origin requests');
 console.log('FT-16 '+browserName+' release-link gate '+checks+'/'+checks+' PASS'+(negative?' NEGATIVE':''));
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
