import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const html=readFileSync(new URL('./index.html',import.meta.url),'utf8');
const app=readFileSync(new URL('./app.mjs',import.meta.url),'utf8');
const css=readFileSync(new URL('./style.css',import.meta.url),'utf8');
let passed=0;
function check(description,test){test();passed++;console.log('PASS '+description);}
check('restrictive CSP declared in page',()=>{
  const match=html.match(/<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"/i);
  assert.ok(match,'Expected CSP meta declaration.');
  for(const directive of ["default-src 'none'","script-src 'self'","style-src 'self'","connect-src 'none'","object-src 'none'","base-uri 'none'","form-action 'none'"]){
    assert.ok(match[1].split(';').some(part=>part.trim()===directive),'Missing '+directive);
  }
});
check('all script and stylesheet URLs stay local',()=>{
  const assets=[...html.matchAll(/<(?:script|link)\b[^>]*(?:src|href)="([^"]+)"/g)].map(m=>m[1]);
  assert.deepEqual(assets,['style.css','app.mjs']);
  assert.match(html,/<script\s+type="module"\s+src="app\.mjs"><\/script>/);
});
check('no inline event handlers or form endpoints',()=>{
  assert.doesNotMatch(html,/\son[a-z]+\s*=/i);
  assert.doesNotMatch(html,/\s(?:action|formaction)\s*=/i);
});
check('all ten user controls have visible labels',()=>{
  const labels=[...html.matchAll(/<label>[\s\S]*?<\/label>/g)].map(m=>m[0]);
  for(const id of ['start','end','opening','event-id','event-label','event-amount','event-date','event-repeat','shift-id','shift-days']){
    assert.ok(labels.some(label=>label.includes('id="'+id+'"')),'Missing visible label for '+id);
  }
});
check('main landmark and data table headers are present',()=>{
  assert.match(html,/<main>/);
  assert.match(html,/<table><caption>[^<]+<\/caption>/);
  assert.equal((html.match(/<th scope="col">/g)||[]).length,4);
});
check('calculations and errors are announced',()=>{
  assert.match(html,/<p id="status" role="status" aria-live="polite">/);
  assert.match(html,/<p id="error" role="alert"><\/p>/);
  assert.match(html,/<ul id="events" aria-live="polite">/);
});
check('visible keyboard focus and small-screen layout rules',()=>{
  assert.match(css,/:focus-visible/);
  assert.match(css,/@media\(max-width:360px\)/);
  assert.match(css,/overflow-x:auto/);
});
check('event descriptions and results are inserted as text',()=>{
  assert.match(app,/\.textContent\s*=/);
  assert.match(app,/document\.createTextNode/);
  assert.doesNotMatch(app,/\.(?:innerHTML|outerHTML)\s*=/);
  assert.doesNotMatch(app,/\b(?:eval|Function)\s*\(/);
});
check('no fetch or remote upload implementation',()=>{
  assert.doesNotMatch(app,/\b(?:fetch|XMLHttpRequest|WebSocket|sendBeacon)\b/);
  assert.match(app,/new Blob\(\[exportCSV\(latest\)\]/);
  assert.match(app,/URL\.revokeObjectURL/);
});
console.log(passed+' FT-04 static security/accessibility guard assertions PASS; browser, CSP enforcement, screen-reader and zoom checks require separate testing.');
