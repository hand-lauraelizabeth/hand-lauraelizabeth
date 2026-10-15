import assert from 'node:assert/strict';
class Element {
  constructor(tag=''){this.tag=tag;this.children=[];this.listeners={};this.value='';this.files=[];this.disabled=false;this.textContent='';this.focused=false;}
  addEventListener(type,fn){this.listeners[type]=fn;}
  dispatch(type){return this.listeners[type]?.();}
  replaceChildren(){this.children=[];}
  append(...items){this.children.push(...items);}
  focus(){this.focused=true;}
}
const ids=['source-json','matrix-search','matrix-mode','matrix-body','matrix-status','matrix-error','matrix-export','matrix-clear'];
const elements=Object.fromEntries(ids.map(id=>[id,new Element()]));
elements['matrix-mode'].value='all';
globalThis.document={getElementById:id=>elements[id],createElement:tag=>new Element(tag)};
let approved=true;
globalThis.confirm=()=>approved;
await import('./matrix-page.mjs');
const payload=id=>JSON.stringify({schema:'evidence-timeline-v1',records:[{sourceId:id,date:'2026-10-14',claim:'Synthetic test',status:'reported',kind:'source',group:''}]});
const file=(id)=>{const raw=payload(id);return {name:id+'.json',size:Buffer.byteLength(raw),arrayBuffer:async()=>new TextEncoder().encode(raw).buffer};};
const upload=async f=>{elements['source-json'].files=[f];await elements['source-json'].dispatch('change');};
assert.equal(elements['matrix-clear'].disabled,true);
await upload(file('A'));
assert.equal(elements['matrix-clear'].disabled,false);
assert.equal(elements['matrix-body'].children.length,1);
approved=false;
elements['matrix-clear'].dispatch('click');
assert.equal(elements['matrix-body'].children.length,1);
approved=true;
elements['matrix-search'].value='A';
elements['matrix-mode'].value='single';
elements['matrix-clear'].dispatch('click');
assert.equal(elements['matrix-body'].children.length,0);
assert.equal(elements['matrix-export'].disabled,true);
assert.equal(elements['matrix-clear'].disabled,true);
assert.equal(elements['matrix-search'].value,'');
assert.equal(elements['matrix-mode'].value,'all');
assert.equal(elements['source-json'].focused,true);
assert.match(elements['matrix-status'].textContent,/reset/);
let release;
const delayedRaw=payload('STALE');
const delayed={name:'stale.json',size:Buffer.byteLength(delayedRaw),arrayBuffer:()=>new Promise(resolve=>{release=()=>resolve(new TextEncoder().encode(delayedRaw).buffer);})};
elements['source-json'].files=[delayed];
const pending=elements['source-json'].dispatch('change');
assert.equal(elements['matrix-clear'].disabled,false);
elements['matrix-clear'].dispatch('click');
assert.equal(elements['source-json'].disabled,false);
release();
await pending;
assert.equal(elements['matrix-body'].children.length,0);
assert.equal(elements['matrix-export'].disabled,true);
assert.equal(elements['matrix-clear'].disabled,true);
assert.match(elements['matrix-status'].textContent,/reset/);
console.log('18 local reset and pending-import regression assertions PASS');
