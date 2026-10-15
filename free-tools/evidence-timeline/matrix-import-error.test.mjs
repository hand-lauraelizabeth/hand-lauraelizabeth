import assert from 'node:assert/strict';
class Element {
  constructor(tag=''){this.tag=tag;this.children=[];this.listeners={};this.value='';this.files=[];this.disabled=false;this.textContent='';}
  addEventListener(type,fn){this.listeners[type]=fn}
  dispatch(type){return this.listeners[type]?.()}
  replaceChildren(){this.children=[]}
  append(...items){this.children.push(...items)}
}
const ids=['source-json','matrix-search','matrix-mode','matrix-body','matrix-status','matrix-error','matrix-export'];
const elements=Object.fromEntries(ids.map(id=>[id,new Element()]));
elements['matrix-mode'].value='all';
globalThis.document={getElementById:id=>elements[id],createElement:tag=>new Element(tag)};
globalThis.confirm=()=>true;
const record=(sourceId)=>JSON.stringify({schema:'evidence-timeline-v1',records:[{sourceId,date:'2026-10-14',claim:'Synthetic',status:'reported',kind:'source',group:''}]});
const file=(name,raw)=>({name,size:Buffer.byteLength(raw),arrayBuffer:async()=>new TextEncoder().encode(raw).buffer});
await import('./matrix-page.mjs');
const upload=async f=>{elements['source-json'].files=[f];await elements['source-json'].dispatch('change')};
await upload(file('first.json',record('FIRST')));
assert.equal(elements['matrix-body'].children[0].children[0].textContent,'FIRST');
assert.equal(elements['matrix-error'].textContent,'');
await upload(file('invalid.txt',record('SECOND')));
assert.match(elements['matrix-error'].textContent,/Import failed:/);
assert.match(elements['matrix-error'].textContent,/Existing records remain available/);
assert.equal(elements['matrix-body'].children[0].children[0].textContent,'FIRST');
assert.equal(elements['matrix-export'].disabled,false);
await upload(file('second.json',record('SECOND')));
assert.equal(elements['matrix-error'].textContent,'');
assert.equal(elements['matrix-body'].children[0].children[0].textContent,'SECOND');
assert.equal(elements['source-json'].disabled,false);
console.log('8 import error recovery assertions PASS');
