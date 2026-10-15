import assert from 'node:assert/strict';
class Element {
 constructor(tag=''){this.tag=tag;this.children=[];this.listeners={};this.value='';this.files=[];this.disabled=false;this.textContent='';this.attributes={};this.focused=false;}
 addEventListener(type,fn){this.listeners[type]=fn;}
 dispatch(type){return this.listeners[type]?.();}
 setAttribute(name,value){this.attributes[name]=String(value);}
 removeAttribute(name){delete this.attributes[name];}
 getAttribute(name){return this.attributes[name]??null;}
 replaceChildren(){this.children=[];}
 append(...items){this.children.push(...items);}
 focus(){this.focused=true;}
}
const ids=['source-json','matrix-search','matrix-mode','matrix-body','matrix-status','matrix-error','matrix-export','matrix-clear'];
const elements=Object.fromEntries(ids.map(id=>[id,new Element()]));
elements['matrix-mode'].value='all';
globalThis.document={getElementById:id=>elements[id],createElement:tag=>new Element(tag)};
globalThis.confirm=()=>true;
await import('./matrix-page.mjs');
const raw=id=>JSON.stringify({schema:'evidence-timeline-v1',records:[{sourceId:id,date:'2026-10-14',claim:'Synthetic',status:'reported',kind:'source',group:''}]});
const file=(name,data)=>({name,size:Buffer.byteLength(data),arrayBuffer:async()=>new TextEncoder().encode(data).buffer});
const upload=async f=>{elements['source-json'].files=[f];await elements['source-json'].dispatch('change');};
const input=elements['source-json'],error=elements['matrix-error'];
const current=()=>elements['matrix-body'].children[0]?.children[0]?.textContent;
assert.equal(input.getAttribute('aria-invalid'),null);
await upload(file('first.json',raw('FIRST')));
assert.equal(current(),'FIRST');
assert.equal(input.getAttribute('aria-invalid'),null);
await upload(file('wrong.txt',raw('BAD')));
assert.equal(input.getAttribute('aria-invalid'),'true');
assert.match(error.textContent,/Import failed/);
assert.equal(current(),'FIRST');
await upload(file('second.json',raw('SECOND')));
assert.equal(input.getAttribute('aria-invalid'),null);
assert.equal(error.textContent,'');
assert.equal(current(),'SECOND');
await upload(file('again.txt',raw('BAD')));
assert.equal(input.getAttribute('aria-invalid'),'true');
elements['matrix-clear'].dispatch('click');
assert.equal(input.getAttribute('aria-invalid'),null);
assert.equal(error.textContent,'');
assert.equal(elements['matrix-body'].children.length,0);
assert.equal(input.focused,true);
let finish;
const delayed=file('delayed.json',raw('DELAYED'));
delayed.arrayBuffer=()=>new Promise(resolve=>{finish=()=>resolve(new TextEncoder().encode(raw('DELAYED')).buffer)});
input.files=[delayed];
const pending=input.dispatch('change');
assert.equal(input.getAttribute('aria-invalid'),null);
elements['matrix-clear'].dispatch('click');
finish();await pending;
assert.equal(elements['matrix-body'].children.length,0);
assert.equal(input.getAttribute('aria-invalid'),null);
console.log('15 synthetic import validation and recovery assertions PASS');
