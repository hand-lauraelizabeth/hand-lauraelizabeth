/** Synthetic-only FT-09 download failure and exact-evidence regression. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {bindExports} from './export-ui.mjs';

const original={document:globalThis.document,setTimeout:globalThis.setTimeout,
  create:URL.createObjectURL,revoke:URL.revokeObjectURL};
let mode='ok',pending=0,created=[],revoked=[],links=[],messages=[];
let state={version:1,requests:[{
  id:'REQ-0001',jurisdiction:'federal',agency:'Synthetic office',stage:'draft',
  submittedOn:'',agencyTrackingId:'',description:'Synthetic evidence 漢字'
}],events:[]};
const handlers={};
globalThis.document={
  getElementById(id){return {addEventListener(type,fn){assert.equal(type,'click');handlers[id]=fn;}};},
  createElement(tag){
    assert.equal(tag,'a');
    const link={attached:false,removed:false,href:'',download:'',
      click(){if(mode==='click')throw new Error('PRIVATE simulated browser exception');},
      remove(){this.removed=true;this.attached=false;}};
    links.push(link);return link;
  },
  body:{append(link){link.attached=true;}}
};
URL.createObjectURL=blob=>{
  if(mode==='create')throw new Error('PRIVATE simulated URL exception');
  created.push(blob);return 'blob:synthetic-'+created.length;
};
URL.revokeObjectURL=url=>{revoked.push(url);};
globalThis.setTimeout=fn=>{fn();return 1;}; // Deterministic URL cleanup in synthetic DOM.
bindExports(()=>state,message=>messages.push(message),()=>pending);
const click=id=>{const n=messages.length;assert.doesNotThrow(()=>handlers[id]());assert.equal(messages.length,n+1);return messages.at(-1);};
const reset=()=>{mode='ok';pending=0;created=[];revoked=[];links=[];messages=[];};
try{
  await test('JSON object URL creation failure is visible and preserves exact evidence',()=>{
    reset();mode='create';
    const result=click('save-json');
    assert.match(result,/JSON download could not start/);
    assert.match(result,/saved records are unchanged/);
    assert.doesNotMatch(result,/PRIVATE|Synthetic evidence/);
    assert.equal(created.length,0);assert.equal(links.length,0);
    assert.equal(state.requests[0].description,'Synthetic evidence 漢字');
  });
  await test('JSON click failure cleans the anchor and revokes the object URL',()=>{
    reset();mode='click';
    const result=click('save-json');
    assert.match(result,/JSON download could not start/);
    assert.equal(created.length,1);assert.equal(links.length,1);
    assert.equal(links[0].removed,true);assert.equal(links[0].attached,false);
    assert.deepEqual(revoked,['blob:synthetic-1']);
  });
  await test('successful retry exports exact JSON and warns about unsaved corrections',async()=>{
    reset();pending=2;
    assert.match(click('save-json'),/2 unsaved corrections were excluded/);
    assert.equal(links[0].removed,true);assert.equal(revoked.length,1);
    assert.deepEqual(JSON.parse(await created[0].text()),state);
  });
  await test('CSV object URL failure is distinguished from CSV validation failure',()=>{
    reset();mode='create';
    assert.match(click('save-csv'),/CSV download could not start/);
    assert.equal(links.length,0);
    assert.doesNotMatch(messages[0],/PRIVATE/);
  });
  await test('formula-risk CSV fails closed; exact JSON remains available',async()=>{
    reset();
    const previous=state;
    state={...state,requests:[{...state.requests[0],description:'=1+1'}]};
    assert.match(click('save-csv'),/CSV unavailable:/);
    assert.equal(created.length,0);
    assert.match(click('save-json'),/JSON downloaded/);
    assert.equal(JSON.parse(await created[0].text()).requests[0].description,'=1+1');
    state=previous;
  });
  await test('valid CSV download retains saved identifiers and synthetic content',async()=>{
    reset();pending=1;
    assert.match(click('save-csv'),/1 unsaved correction was excluded/);
    const csv=await created[0].text();
    assert.match(csv,/"REQ-0001"/);
    assert.match(csv,/"Synthetic evidence 漢字"/);
    assert.equal(links[0].removed,true);
  });
}finally{
  globalThis.document=original.document;globalThis.setTimeout=original.setTimeout;
  URL.createObjectURL=original.create;URL.revokeObjectURL=original.revoke;
}
