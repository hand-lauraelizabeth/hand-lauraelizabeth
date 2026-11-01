/**
 * FT-16: actual keyboard navigation and Referer suppression at the browser boundary.
 * Synthetic catalog and intercepted destination only: never contacts the public site.
 * HTML Living Standard, 2026-10-30: https://html.spec.whatwg.org/multipage/links.html#link-type-noreferrer
 * W3C Referrer Policy: https://www.w3.org/TR/referrer-policy/#referrer-policy-no-referrer
 * The fixture deliberately sets an unsafe document referrer policy so the
 * missing-noreferrer negative control is observable in real browsers.
 * Touch mode uses Playwright's hasTouch context and locator.tap(), not a
 * physical device. Source: https://playwright.dev/docs/api/class-locator#locator-tap
 */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium,firefox,webkit} from 'playwright';

const browserName=process.argv[2]||'chromium';
const negative=process.argv.includes('--negative-control');
const touch=process.argv.includes('--touch');
const engine={chromium,firefox,webkit}[browserName];
if(!engine)throw Error('Unsupported browser '+browserName);
const dir=dirname(fileURLToPath(import.meta.url));
const target='https://www.lauraelizabethhand.com/resources/synthetic-tool/';
const fixture=[
 {id:'synthetic-live',title:'Synthetic live resource',category:'Research',
  description:'Synthetic private-marker-FT16 local navigation test',status:'live',url:target},
 {id:'synthetic-development',title:'Synthetic unreleased resource',category:'Research',
  description:'Never navigate to this entry',status:'development'}
];
const allowed=new Set(['index.html','app.mjs','catalog.mjs','directory.mjs',
 'styles.css','layout.css','controls.css','focus.css']);
const csp="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'self' data:; font-src 'self'; object-src 'none'; form-action 'none'; base-uri 'none'";
const server=createServer(async(req,res)=>{
 const name=new URL(req.url,'http://localhost').pathname.slice(1)||'index.html';
 if(!allowed.has(name)){res.writeHead(404);res.end('Not found');return;}
 try{
  let source=name==='catalog.mjs'
   ? 'export const TOOLS='+JSON.stringify(fixture)+';\nexport const STATUS_LABELS={live:"Live",preview:"Preview",development:"In development"};\n'
   :await readFile(join(dir,name),'utf8');
  if(negative&&name==='app.mjs'){
   const guard="a.rel='noreferrer'";
   assert.ok(source.includes(guard),'negative control must remove the actual referrer guard');
   source=source.replace(guard,"a.rel=''");
  }
  const type=name.endsWith('.html')?'text/html':name.endsWith('.css')?'text/css':'text/javascript';
  res.writeHead(200,{'Content-Type':type+'; charset=utf-8',
   'X-Content-Type-Options':'nosniff','Content-Security-Policy':csp,
   'Referrer-Policy':'unsafe-url'});
  res.end(source);
 }catch{res.writeHead(500);res.end('Synthetic fixture failed');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser,checks=0;
const eq=(actual,expected,label)=>{assert.deepEqual(actual,expected,label);checks++;};
try{
 browser=await engine.launch({headless:true});
 const page=await browser.newPage({hasTouch:touch,viewport:{width:touch?375:320,height:720}});
 const errors=[],outbound=[],intercepted=[];
 const local='http://127.0.0.1:'+server.address().port;
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(!r.url().startsWith(local+'/'))outbound.push(r.url());});
 await page.route('https://www.lauraelizabethhand.com/**',async route=>{
  intercepted.push({url:route.request().url(),headers:await route.request().allHeaders()});
  await route.fulfill({status:200,contentType:'text/html',
   body:'<!doctype html><title>Synthetic destination</title><h1>Intercepted locally</h1>'});
 });
 const response=await page.goto(local+'/?source=synthetic-secret-FT16',{waitUntil:'networkidle'});
 eq(response.status(),200,'directory served over HTTP');
 eq(response.headers()['referrer-policy'],'unsafe-url','negative-control-sensitive document policy is active');
 eq(response.headers()['content-security-policy'],csp,'enforced directory CSP');
 eq(await page.locator('#tool-query').isEnabled(),true,'directory initialized');
 eq(await page.locator('.ft15-link').count(),1,'only approved live entry has link');
 eq(await page.locator('.ft15-unavailable').count(),1,'unreleased entry remains unlinked');
 await page.locator('#tool-query').fill('private-marker-FT16');
 eq(await page.locator('.ft15-link').count(),1,'local synthetic search retains live destination');
 eq(await page.locator('.ft15-link').getAttribute('href'),target,'exact canonical destination');
 eq(await page.locator('.ft15-link').getAttribute('rel'),negative?'':'noreferrer','actual link relation');
 eq(outbound,[],'no outbound request from search');
 eq(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),
  true,'narrow viewport reflows without horizontal overflow');
 if(touch){
  eq(await page.evaluate(()=>'ontouchstart' in window),true,'browser touch input enabled');
 }else{
  await page.locator('.ft15-link').focus();
  eq(await page.locator('.ft15-link').evaluate(el=>el===document.activeElement),true,'link keyboard-focusable');
 }
 await Promise.all([
  page.waitForURL(target),
  touch?page.locator('.ft15-link').tap():page.keyboard.press('Enter')
 ]);
 eq(await page.title(),'Synthetic destination','keyboard navigation reached intercepted page');
 eq(intercepted.length,1,'exactly one intercepted destination request');
 eq(intercepted[0].url,target,'no search terms or identifiers appended to destination');
 eq(Object.hasOwn(intercepted[0].headers,'referer'),false,
  'actual navigation must omit Referer even under unsafe-url document policy');
 eq(outbound,[target],'only the deliberately intercepted navigation leaves local origin');
 eq(errors,[],'no application exceptions');
 console.log('FT-16 '+browserName+' '+(touch?'touch':'keyboard')+
  ' intercepted navigation privacy '+checks+'/'+checks+' PASS');
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
