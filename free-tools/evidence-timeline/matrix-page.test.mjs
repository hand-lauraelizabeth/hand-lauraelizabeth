import assert from 'node:assert/strict';
class El {
  constructor(tag=''){this.tag=tag;this.children=[];this.listeners={};this.value='';this.files=[];this.disabled=false;this.textContent='';}
  addEventListener(type,fn){this.listeners[type]=fn}
  dispatch(type){return this.listeners[type]?.()}
  replaceChildren(){this.children=[]}
  append(...items){this.children.push(...items)}
  click(){if(this.tag==='a')globalThis.downloaded={url:this.href,name:this.download}}
}
const ids=['source-json','matrix-search','matrix-mode','matrix-body','matrix-status','matrix-export'];
const elements=Object.fromEntries(ids.map(id=>[id,new El()]));
elements['matrix-mode'].value='all';
globalThis.document={getElementById:id=>elements[id],createElement:tag=>new El(tag)};
globalThis.confirm=()=>true;
let exported;
URL.createObjectURL=blob=>{exported=blob;return 'blob:local-test'};
URL.revokeObjectURL=()=>{};
globalThis.setTimeout=fn=>fn();
await import('./matrix-page.mjs');
assert.equal(elements['matrix-export'].disabled,true);
const records=Array.from({length:300},(_,i)=>({sourceId:'S'+i,date:'2026-10-14',claim:i===0?'=1+1':'Synthetic '+i,status:'reported',kind:'source',group:'batch'}));
const raw=JSON.stringify({schema:'evidence-timeline-v1',records});
elements['source-json'].files=[{name:'synthetic.json',size:raw.length,arrayBuffer:async()=>new TextEncoder().encode(raw).buffer}];
await elements['source-json'].dispatch('change');
assert.equal(elements['matrix-body'].children.length,250);
assert.equal(elements['matrix-export'].disabled,false);
elements['matrix-export'].dispatch('click');
const csv=await exported.text();
assert.equal(csv.split('\r\n').length,302);
assert.ok(csv.includes("'=1+1"));
elements['matrix-search'].value='S299';
elements['matrix-search'].dispatch('input');
assert.equal(elements['matrix-body'].children.length,1);
elements['matrix-mode'].value='ungrouped';
elements['matrix-mode'].dispatch('change');
assert.equal(elements['matrix-body'].children.length,0);
assert.equal(elements['matrix-export'].disabled,true);
console.log('8 synthetic matrix controller checks PASS');
