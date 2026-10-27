'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'..','text-lens.html'),'utf8');
const start=html.indexOf('const MAX_LOCAL_FILES=20,MAX_LOCAL_BYTES=5000000;');
const end=html.indexOf('function publicResult(r){',start);
assert.ok(start>0&&end>start,'Strict browser-local loader must exist');
const source=html.slice(start,end);
const encoder=new TextEncoder();
function file(name,text,overrides={}){
 const raw=typeof text==='string'?encoder.encode(text):Uint8Array.from(text);
 return {name,size:raw.byteLength,lastModified:42,arrayBuffer:async()=>raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength),...overrides};
}
function harness(withExternalImport=false){
 const els={};
 for(const id of ['a','b','fileMetaA','fileMetaB','status']){
  els[id]={value:'',textContent:'',focused:false,focus(){this.focused=true}};
 }
 let runs=0;
 const handlers={};
 const env={
  root:{addEventListener(type,handler){handlers[type]=handler}},
  MAX_CHARS:400000,sourceDocs:{a:[],b:[]},sourceFiles:{a:[],b:[]},
  docSeq:0,pendingCorpusConfig:null,run(){runs++},applyCorpusSetup(){runs++},
  $(id){return els[id]},TextDecoder,Uint8Array,ArrayBuffer,Number,String,Error
 };
 const eventStart=html.indexOf("root.addEventListener('text-lens:import',e=>{");
 const eventEnd=html.indexOf('});run();})();',eventStart);
 assert.ok(eventStart>0&&eventEnd>eventStart,'External import event handler must exist');
 const eventHandler=html.slice(eventStart,eventEnd+2);
 const api=vm.runInNewContext(source+(withExternalImport?'\n'+eventHandler:'')+';({loadFiles,fileLoadRevision,getDocSeq:()=>docSeq})',env);
 return {api,env,els,handlers,get runs(){return runs}};
}
test('strict UTF-8 import preserves Unicode, exact source names and stable IDs',async()=>{
 const h=harness();
 await h.api.loadFiles({files:[file('0001.md','Café 😀'),file('日本語.csv','001,東京')],value:'chosen'},'a','fileMetaA','a');
 assert.equal(h.els.a.value,'Café 😀\n\n001,東京');
 assert.deepEqual(Array.from(h.env.sourceDocs.a,x=>x.id),['a-1','a-2']);
 assert.equal(h.env.sourceDocs.a[1].name,'日本語.csv');
 assert.equal(h.api.getDocSeq(),2);
 assert.equal(h.runs,1);
 assert.equal(h.els.a.focused,true);
});
test('malformed UTF-8 fails closed without overwriting prior corpus',async()=>{
 const h=harness();h.env.sourceDocs.a=[{id:'a-7',text:'keep'}];h.els.a.value='keep';
 const input={files:[file('bad.txt',[0xc3,0x28])],value:'chosen'};
 await h.api.loadFiles(input,'a','fileMetaA','a');
 assert.match(h.els.status.textContent,/Invalid UTF-8/);
 assert.equal(h.els.status.focused,true);
 assert.equal(h.els.status.tabIndex,-1);
 assert.equal(h.els.a.value,'keep');
 assert.equal(h.env.sourceDocs.a[0].id,'a-7');
 assert.equal(h.api.getDocSeq(),0);
 assert.equal(input.value,'');
});
test('metadata size limits reject before reading bytes',async()=>{
 const h=harness();let reads=0;
 const large=file('large.txt','x',{size:5000001,arrayBuffer:async()=>{reads++;return new ArrayBuffer(0)}});
 await h.api.loadFiles({files:[large],value:'x'},'a','fileMetaA','a');
 assert.equal(reads,0);
 assert.match(h.els.status.textContent,/byte local limit/);
 assert.equal(h.runs,0);
});
test('file count, type and empty input reject without changing corpus',async()=>{
 for(const files of [
  Array.from({length:21},(_,i)=>file(i+'.txt','x')),
  [file('bad.exe','x')],
  [file('empty.md','',{size:0})]
 ]){
  const h=harness();h.els.a.value='original';
  await h.api.loadFiles({files,value:'x'},'a','fileMetaA','a');
  assert.equal(h.els.a.value,'original');
  assert.equal(h.api.getDocSeq(),0);
  assert.equal(h.runs,0);
  assert.ok(h.els.status.textContent);
 }
});
test('changed byte count, binary NUL and combined character limit reject atomically',async()=>{
 for(const files of [
  [file('size.txt','abc',{size:4})],
  [file('binary.csv',[65,0,66])],
  [file('a.txt','x'.repeat(250000)),file('b.txt','y'.repeat(150000))]
 ]){
  const h=harness();h.els.a.value='original';
  await h.api.loadFiles({files,value:'x'},'a','fileMetaA','a');
  assert.equal(h.els.a.value,'original');
  assert.equal(h.runs,0);
  assert.equal(h.api.getDocSeq(),0);
  assert.ok(h.els.status.focused);
 }
});
test('older asynchronous selection cannot replace a newer successful selection',async()=>{
 const h=harness();let resolve;
 const delayed=file('old.txt','old',{arrayBuffer:()=>new Promise(r=>resolve=r)});
 const old=h.api.loadFiles({files:[delayed],value:'old'},'a','fileMetaA','a');
 await h.api.loadFiles({files:[file('new.txt','new')],value:'new'},'a','fileMetaA','a');
 resolve(encoder.encode('old').buffer);await old;
 assert.equal(h.els.a.value,'new');
 assert.deepEqual(Array.from(h.env.sourceDocs.a,x=>x.name),['new.txt']);
 assert.equal(h.runs,1);
 assert.equal(h.api.getDocSeq(),1);
});
test('clear or manual edit invalidates pending read without stale focus or error',async()=>{
 const h=harness();let resolve;
 const delayed=file('old.txt','old',{arrayBuffer:()=>new Promise(r=>resolve=r)});
 const old=h.api.loadFiles({files:[delayed],value:'old'},'a','fileMetaA','a');
 h.api.fileLoadRevision.a++;
 h.els.a.value='manually edited';
 resolve(encoder.encode('old').buffer);await old;
 assert.equal(h.els.a.value,'manually edited');
 assert.equal(h.runs,0);
 assert.equal(h.els.status.textContent,'');
 assert.equal(h.els.a.focused,false);
 assert.ok(html.includes("['a','b'].forEach(id=>$(id).addEventListener('input',()=>{fileLoadRevision[id]++}))"));
 assert.ok(html.includes("$('clear').onclick=()=>{fileLoadRevision.a++;fileLoadRevision.b++;"));
 assert.ok(html.includes("$('sample').onclick=()=>{fileLoadRevision.a++;fileLoadRevision.b++;"));
});

test('external corpus import cancels an older pending file read on the same side',async()=>{
 const h=harness(true);let resolve;
 const pending=h.api.loadFiles({files:[file('old.txt','old',{arrayBuffer:()=>new Promise(r=>resolve=r)})],value:'old'},'a','fileMetaA','a');
 assert.equal(typeof h.handlers['text-lens:import'],'function');
 h.handlers['text-lens:import']({detail:{key:'a',name:'new-東京.md',size:3,lastModified:77,text:'new'}});
 resolve(encoder.encode('old').buffer);await pending;
 assert.deepEqual(Array.from(h.env.sourceDocs.a,x=>x.name),['new-東京.md']);
 assert.deepEqual(Array.from(h.env.sourceFiles.a),['new-東京.md']);
 assert.equal(h.api.getDocSeq(),1);
 assert.equal(h.api.fileLoadRevision.a,2);
 assert.equal(h.runs,1);
 assert.match(h.els.fileMetaA.textContent,/new-東京.md/);
 assert.equal(h.els.a.focused,false);
});
test('external import invalidates only its own side, preserving another pending file',async()=>{
 const h=harness(true);let resolve;
 const pending=h.api.loadFiles({files:[file('a.txt','AAA',{arrayBuffer:()=>new Promise(r=>resolve=r)})],value:'a'},'a','fileMetaA','a');
 h.handlers['text-lens:import']({detail:{key:'b',name:'b-0001.csv',size:3,lastModified:5,text:'BBB'}});
 h.handlers['text-lens:import']({detail:{key:'invalid',name:'ignored.txt',text:'x'}});
 resolve(encoder.encode('AAA').buffer);await pending;
 assert.equal(h.els.a.value,'AAA');
 assert.deepEqual(Array.from(h.env.sourceDocs.a,x=>x.name),['a.txt']);
 assert.deepEqual(Array.from(h.env.sourceDocs.b,x=>x.name),['b-0001.csv']);
 assert.equal(h.api.fileLoadRevision.a,1);
 assert.equal(h.api.fileLoadRevision.b,1);
 assert.equal(h.api.getDocSeq(),2);
 assert.equal(h.runs,2);
});
