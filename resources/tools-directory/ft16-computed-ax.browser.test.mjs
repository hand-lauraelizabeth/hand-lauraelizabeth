/**
 * FT-16: Verify Chromium's computed accessibility tree, not only DOM attributes.
 * HTTP-served with the directory CSP and synthetic search strings.
 * Sources reviewed 2026-10-30:
 * https://www.w3.org/TR/accname-1.2/
 * https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/
 * This checks browser-exposed names/descriptions; it is not a screen-reader test.
 */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const negative=process.argv.includes('--negative-control');
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
   assert.ok(data.includes('id="tool-search-help"'),'negative fixture must match');
   data=data.replace('id="tool-search-help"','id="tool-search-help-removed"');
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
function yes(value,label){assert.ok(value,label);checks++;}
try{
 browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:320,height:720}});
 const page=await context.newPage();
 const errors=[],external=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('request',request=>{
  if(!request.url().startsWith('http://127.0.0.1:'+server.address().port+'/'))
   external.push(request.url());
 });
 const response=await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'networkidle'});
 eq(response.status(),200,'HTTP page');
 eq(response.headers()['content-security-policy'],csp,'real CSP response');
 eq(await page.locator('#tool-query').isEnabled(),true,'initialized controls');
 const session=await context.newCDPSession(page);
 await session.send('Accessibility.enable');
 async function ax(){
  const doc=await session.send('DOM.getDocument',{depth:1});
  const node=await session.send('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'#tool-query'});
  yes(node.nodeId>0,'query DOM node exists');
  const tree=await session.send('Accessibility.getPartialAXTree',
   {nodeId:node.nodeId,fetchRelatives:false});
  const input=tree.nodes.find(n=>n.backendDOMNodeId&&n.role?.value==='searchbox');
  yes(!!input,'searchbox is exposed in Chromium accessibility tree');
  return {
   name:input.name?.value||'',
   description:input.description?.value||'',
   invalid:input.properties?.find(p=>p.name==='invalid')?.value?.value
  };
 }
 const query=page.locator('#tool-query');
 let state=await ax();
 eq(state.name,'Search tools','native label becomes computed accessible name');
 yes(state.description.includes('256 Unicode code points'),'normal computed description contains limit');
 yes(state.description.includes('Searches stay in your browser'),'normal computed description includes privacy');
 eq(state.invalid,'false','normal AX invalid state');
 await query.fill('a'.repeat(257));
 state=await ax();
 yes(state.description.includes('256 Unicode code points'),'overlength retains help in AX description');
 yes(state.description.includes('Shorten your query'),'overlength adds actionable error in AX description');
 eq(state.invalid,'true','overlength exposed as invalid in AX tree');
 await query.fill('🎓'+String.fromCodePoint(0x202e)+' research');
 state=await ax();
 yes(state.description.includes('Searches stay in your browser'),'Unicode error retains help in AX tree');
 yes(state.description.includes('code point 2 (U+202E)'),'Unicode error location reaches AX tree');
 eq(state.invalid,'true','Unicode input exposed as invalid');
 await query.fill('research');
 state=await ax();
 yes(state.description.includes('Searches stay in your browser'),'corrected query retains help');
 eq(state.description.includes('U+202E'),false,'corrected query clears stale Unicode error');
 eq(state.description.includes('Shorten your query'),false,'corrected query clears stale length error');
 eq(state.invalid,'false','correction clears AX invalid state');
 await page.locator('#tool-clear').click();
 state=await ax();
 eq(state.name,'Search tools','clear preserves accessible name');
 yes(state.description.includes('256 Unicode code points'),'clear preserves computed description');
 eq(await query.evaluate(el=>document.activeElement===el),true,'clear restores focus');
 eq(errors,[],'no page errors');
 eq(external,[],'no off-origin requests');
 console.log('FT-16 Chromium computed accessibility tree '+checks+'/'+checks+' PASS');
 await context.close();
}finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
}
