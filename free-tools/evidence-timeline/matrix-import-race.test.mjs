import assert from 'node:assert/strict';
class El {
 constructor(tag=''){this.tag=tag;this.children=[];this.listeners={};this.value='';this.files=[];this.disabled=false;this.textContent='';}
 setAttribute(k,v){this[k]=v}
 removeAttribute(k){delete this[k]}
 addEventListener(k,f){this.listeners[k]=f}
 dispatch(k){return this.listeners[k]?.()}
 replaceChildren(){this.children=[]}
 append(...x){this.children.push(...x)}
 click(){}
}
const ids=['source-json','matrix-search','matrix-mode','matrix-body','matrix-status','matrix-export','matrix-clear','matrix-error'];
const els=Object.fromEntries(ids.map(id=>[id,new El()]));
els['matrix-mode'].value='all';
globalThis.document={getElementById:id=>els[id],createElement:tag=>new El(tag)};
globalThis.confirm=()=>true;
globalThis.setTimeout=fn=>fn();
await import('./matrix-page.mjs');
const make=(id)=>JSON.stringify({schema:'evidence-timeline-v1',records:[{sourceId:id,date:'2026-10-14',claim:'Synthetic',status:'reported',kind:'source',group:'g'}]});
let finishOld;
const old=make('OLD'),latest=make('NEW');
const deferred={name:'old.json',size:old.length,arrayBuffer:()=>new Promise(resolve=>{finishOld=()=>resolve(new TextEncoder().encode(old).buffer)})};
const ready={name:'new.json',size:latest.length,arrayBuffer:async()=>new TextEncoder().encode(latest).buffer};
els['source-json'].files=[deferred];
const first=els['source-json'].dispatch('change');
assert.equal(els['source-json'].disabled,true);
els['source-json'].files=[ready];
const second=els['source-json'].dispatch('change');
await second;
assert.equal(els['matrix-body'].children.length,1);
assert.ok(els['matrix-status'].textContent.includes('1 of 1'));
assert.equal(els['source-json'].disabled,false);
finishOld();
await first;
assert.equal(els['matrix-body'].children.length,1);
assert.equal(els['source-json'].disabled,false);
els['matrix-search'].value='OLD';els['matrix-search'].dispatch('input');
assert.equal(els['matrix-body'].children.length,0);
els['matrix-search'].value='NEW';els['matrix-search'].dispatch('input');
assert.equal(els['matrix-body'].children.length,1);
console.log('6 stale-import race checks PASS');
