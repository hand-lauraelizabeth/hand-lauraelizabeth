/**
 * FT-16: synthetic private search must remain in memory, not URL/history,
 * cookies, Web Storage or outbound requests. No actual personal data.
 * WHATWG HTML Web Storage, updated 2026-10-30:
 * https://html.spec.whatwg.org/multipage/webstorage.html
 * WHATWG History interface, updated 2026-10-30:
 * https://html.spec.whatwg.org/multipage/nav-history-apis.html#the-history-interface
 * W3C CSP3 Working Draft, 2026-10-27:
 * https://www.w3.org/TR/CSP3/#directive-connect-src
 * Browser automation is not a full privacy or accessibility audit.
 */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium,firefox,webkit} from 'playwright';

const browserName=process.argv[2]||'chromium';
const negative=process.argv.includes('--negative-control');
const engine={chromium,firefox,webkit}[browserName];
if(!engine)throw Error('Unsupported browser '+browserName);
const dir=dirname(fileURLToPath(import.meta.url));
const marker='private-marker-FT16-α🙂';
const fixture=[
 {id:'synthetic-live',title:'Synthetic live resource',category:'Research',
  description:'Locally searchable '+marker,status:'live',
  url:'https://www.lauraelizabethhand.com/resources/synthetic-tool/'},
 {id:'synthetic-development',title:'Synthetic development resource',category:'Research',
  description:'Not yet available',status:'development'}
];
const allowed=new Set(['index.html','app.mjs','catalog.mjs','directory.mjs',
 'styles.css','layout.css','controls.css','focus.css']);
const csp="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'self' data:; font-src 'self'; object-src 'none'; form-action 'none'; base-uri 'none'";
const server=createServer(async(req,res)=>{
 const name=new URL(req.url,'http://localhost').pathname.slice(1)||'index.html';
 if(!allowed.has(name)){res.writeHead(404);res.end('Not found');return;}
 try{
  let source=name==='catalog.mjs'
   ?'export const TOOLS='+JSON.stringify(fixture)+';\nexport const STATUS_LABELS={live:"Live",preview:"Preview",development:"In development"};\n'
   :await readFile(join(dir,name),'utf8');
  if(negative&&name==='app.mjs'){
   const guard='const issue=queryIssue(query.value);';
   assert.ok(source.includes(guard),'negative control must modify exact live render path');
   source=source.replace(guard,"localStorage.setItem('ft16-query',query.value);"+guard);
  }
  const type=name.endsWith('.html')?'text/html':name.endsWith('.css')?'text/css':'text/javascript';
  res.writeHead(200,{'Content-Type':type+'; charset=utf-8',
   'X-Content-Type-Options':'nosniff','Content-Security-Policy':csp});
  res.end(source);
 }catch{res.writeHead(500);res.end('Synthetic fixture failed');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser,checks=0;
const eq=(actual,expected,label)=>{assert.deepEqual(actual,expected,label);checks++;};
try{
 browser=await engine.launch({headless:true});
 const page=await browser.newPage({viewport:{width:375,height:720}});
 const errors=[],requests=[];
 const local='http://127.0.0.1:'+server.address().port;
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>requests.push(r.url()));
 const response=await page.goto(local+'/',{waitUntil:'networkidle'});
 eq(response.status(),200,'real local HTTP document');
 eq(response.headers()['content-security-policy'],csp,'CSP is enforced by HTTP header');
 eq(await page.locator('#tool-query').isEnabled(),true,'search initialized');
 eq(await page.locator('.ft15-card').count(),2,'two synthetic resources');
 const initial=await page.evaluate(()=>({
  url:location.href,historyLength:history.length,historyState:history.state
 }));
 const initialRequests=requests.slice();
 await page.locator('#tool-query').fill(marker);
 eq(await page.locator('#tool-query').inputValue(),marker,'exact Unicode search retained in input');
 eq(await page.locator('.ft15-card').count(),1,'private search filters local catalog');
 eq(await page.locator('.ft15-card h3').innerText(),'Synthetic live resource','correct result retained');
 eq(await page.locator('.ft15-link').count(),1,'only live result linked');
 eq(await page.locator('#tool-query-error').isHidden(),true,'valid query has no error');
 const privacy=await page.evaluate(()=>({
  url:location.href,historyLength:history.length,historyState:history.state,
  localStorage:Object.entries(localStorage),sessionStorage:Object.entries(sessionStorage),
  cookies:document.cookie
 }));
 eq(privacy.url,initial.url,'query not written to location or hash');
 eq(privacy.historyLength,initial.historyLength,'query does not create browser history entries');
 eq(privacy.historyState,initial.historyState,'query not written into history.state');
 eq(privacy.localStorage,[],'no localStorage persistence of query');
 eq(privacy.sessionStorage,[],'no sessionStorage persistence of query');
 eq(privacy.cookies,'','no cookie persistence of query');
 eq(requests,initialRequests,'typing makes no network requests');
 eq(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),
  true,'375px viewport has no horizontal overflow');
 await page.locator('#tool-clear').click();
 eq(await page.locator('#tool-query').inputValue(),'','clear removes search text');
 eq(await page.locator('#tool-query').evaluate(el=>el===document.activeElement),
  true,'clear restores keyboard focus to search');
 eq(await page.locator('.ft15-card').count(),2,'clear restores all resources');
 eq(await page.evaluate(()=>[localStorage.length,sessionStorage.length,document.cookie]),
  [0,0,''],'clear leaves no persistent search data');
 eq(requests,initialRequests,'clear makes no network requests');
 eq(errors,[],'no application exceptions');
 console.log('FT-16 '+browserName+' local search privacy '+checks+'/'+checks+' PASS');
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
