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
  $(id){return els[id]},TextDecoder,TextEncoder,Uint8Array,ArrayBuffer,Number,String,Error
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

test('external import rejects malformed or oversized event data without altering evidence',()=>{
 const bad=[
  {text:'x'.repeat(400001)},
  {text:'x\u0000y'},
  {text:null},
  {text:''},
  {text:'bad\uD800'},
  {name:''},
  {name:'reverse\u202Etxt.md'},
  {name:'line\nname.md'},
  {name:'isolate\u2066.txt'},
  {name:'bad\uD800.md'},
  {name:'x'.repeat(256)},
  {name:'bad\u0000.txt'},
  {size:-1},
  {size:0},
  {size:2},
  {size:5000001},
  {size:NaN},
  {lastModified:-1},
  {lastModified:1.5}
 ];
 for(const variant of bad){
  const h=harness(true);
  h.env.sourceDocs.a=[{id:'a-0007',name:'prior.txt',text:'keep'}];
  h.env.sourceFiles.a=['prior.txt'];
  h.els.a.value='keep';
  const detail={key:'a',name:'new-東京.md',size:3,lastModified:77,text:'new',...variant};
  h.handlers['text-lens:import']({detail});
  assert.deepEqual(Array.from(h.env.sourceDocs.a,x=>x.id),['a-0007']);
  assert.deepEqual(Array.from(h.env.sourceFiles.a),['prior.txt']);
  assert.equal(h.els.a.value,'keep');
  assert.equal(h.api.fileLoadRevision.a,0);
  assert.equal(h.api.getDocSeq(),0);
  assert.equal(h.runs,0);
  assert.match(h.els.status.textContent,/Import rejected:/);
  assert.equal(h.els.status.tabIndex,-1);
  assert.equal(h.els.status.focused,true);
 }
});
test('local file source labels reject directional controls without replacing evidence',async()=>{
 for(const name of ['reversal\\u202Etxt.md','newline\\nname.md','isolate\\u2066.txt','bad\\uD800.md']){
  const actual=name.replace(/\\\\u202E/g,'\\u202E').replace(/\\\\n/g,'\\n').replace(/\\\\u2066/g,'\\u2066').replace(/\\\\uD800/g,'\\uD800');
  const h=harness();h.els.a.value='keep';
  const input={files:[file(actual,'safe')],value:'chosen'};
  await h.api.loadFiles(input,'a','fileMetaA','a');
  assert.equal(h.els.a.value,'keep');
  assert.equal(h.api.getDocSeq(),0);
  assert.equal(h.runs,0);
  assert.match(h.els.status.textContent,/Invalid source filename/);
  assert.equal(h.els.status.focused,true);
  assert.equal(input.value,'');
 }
});

test('cross-component imports require truthful UTF-8 bytes and preserve exact Unicode',()=>{
 const h=harness(true);
 const dispatch=(text,size,name='0007-Café-東京.md')=>
  h.handlers['text-lens:import']({detail:{key:'a',name,size,text}});
 const text='Café 😀 東京';
 dispatch(text,1);
 assert.equal(h.api.getDocSeq(),0);
 assert.equal(h.runs,0);
 assert.match(h.els.status.textContent,/byte size does not match/);
 dispatch('bad\\uD800',Buffer.byteLength('bad\\uD800','utf8'));
 assert.equal(h.api.getDocSeq(),0);
 assert.match(h.els.status.textContent,/invalid Unicode surrogate/);
 dispatch(text,Buffer.byteLength(text,'utf8'));
 assert.equal(h.api.getDocSeq(),1);
 assert.equal(h.runs,1);
 assert.equal(h.env.sourceDocs.a[0].name,'0007-Café-東京.md');
 assert.equal(h.env.sourceDocs.a[0].size,Buffer.byteLength(text,'utf8'));
 assert.equal(h.els.a.value,text);
});

test('rejected external event does not cancel an in-flight valid local read',async()=>{
 const h=harness(true);let resolve;
 const pending=h.api.loadFiles({files:[file('valid.txt','yes',{arrayBuffer:()=>new Promise(r=>resolve=r)})],value:'valid'},'a','fileMetaA','a');
 h.handlers['text-lens:import']({detail:{key:'a',name:'oversized.txt',size:1,text:'x'.repeat(400001)}});
 assert.equal(h.api.fileLoadRevision.a,1);
 resolve(encoder.encode('yes').buffer);await pending;
 assert.deepEqual(Array.from(h.env.sourceDocs.a,x=>x.name),['valid.txt']);
 assert.equal(h.runs,1);
 assert.equal(h.api.getDocSeq(),1);
});
test('valid external event recovers after rejection with Unicode source ID intact',()=>{
 const h=harness(true);
 const dispatch=detail=>h.handlers['text-lens:import']({detail});
 dispatch({key:'a',name:'bad',size:5000001,text:'bad'});
 dispatch({key:'a',name:'0001-東京.md',size:5,lastModified:0,text:'Café'});
 assert.deepEqual(Array.from(h.env.sourceDocs.a,x=>x.name),['0001-東京.md']);
 assert.equal(h.env.sourceDocs.a[0].text,'Café');
 assert.equal(h.api.fileLoadRevision.a,1);
 assert.equal(h.api.getDocSeq(),1);
 assert.equal(h.runs,1);
});


test('external import synchronizes the exact analyzed textarea with source provenance on both sides',()=>{
 const h=harness(true);
 h.els.a.value='Older A';h.els.b.value='Older B';
 const textA='Café 東京\n0007,=SUM(1,2)';
 const textB='<img src=x onerror=alert(1)> — literal source text';
 const dispatch=detail=>h.handlers['text-lens:import']({detail});
 dispatch({key:'a',name:'0001-東京.md',size:Buffer.byteLength(textA,'utf8'),lastModified:77,text:textA});
 assert.equal(h.els.a.value,textA);
 assert.equal(h.env.sourceDocs.a[0].text,h.els.a.value);
 assert.equal(h.env.sourceDocs.a[0].name,'0001-東京.md');
 assert.equal(h.els.b.value,'Older B');
 dispatch({key:'b',name:'b-0002.txt',size:Buffer.byteLength(textB,'utf8'),text:textB});
 assert.equal(h.els.b.value,textB);
 assert.equal(h.env.sourceDocs.b[0].text,h.els.b.value);
 assert.equal(h.els.a.value,textA);
 assert.deepEqual(Array.from(h.env.sourceFiles.a),['0001-東京.md']);
 assert.deepEqual(Array.from(h.env.sourceFiles.b),['b-0002.txt']);
 assert.equal(h.api.getDocSeq(),2);
 assert.equal(h.runs,2);
});
test('rejected external import leaves analyzed text and source evidence synchronized',()=>{
 const h=harness(true);
 const dispatch=detail=>h.handlers['text-lens:import']({detail});
 dispatch({key:'a',name:'valid.txt',size:4,text:'safe'});
 dispatch({key:'a',name:'bad.txt',size:-1,text:'different'});
 assert.equal(h.els.a.value,'safe');
 assert.equal(h.env.sourceDocs.a[0].text,'safe');
 assert.equal(h.env.sourceDocs.a[0].name,'valid.txt');
 assert.equal(h.api.fileLoadRevision.a,1);
 assert.equal(h.api.getDocSeq(),1);
 assert.equal(h.runs,1);
 assert.match(h.els.status.textContent,/Import rejected/);
});


test('table CSV fails closed on formula-like source names and retains exact JSON-compatible rows',()=>{
 const start=html.indexOf('function csvEscape(v){'),end=html.indexOf('function docDescriptor(',start);
 const riskStart=html.indexOf('function cueCsvRisk(value){'),riskEnd=html.indexOf('function cueCsvCell(',riskStart);
 assert.ok(start>0&&end>start&&riskStart>0&&riskEnd>riskStart);
 const source=html.slice(riskStart,riskEnd)+'\n'+html.slice(start,end);
 const status={textContent:'',focused:false,focus(){this.focused=true}};
 const create=name=>{
  const docs={a:[{id:'a-1',name,text:'safe words'}],b:[]};
  const context={
   sourceDocs:docs,lastA:{W:2,freq:{safe:2},collocs:[]},lastB:null,lastCompare:false,
   topEntries:freq=>Object.entries(freq),corpusRows:()=>[],corpusComparison:()=>({similarity:[],keyness:[]}),
   kwicTarget:()=>null,kwic:()=>[],analyze:()=>({W:2,flesch:-3,mattr50:NaN,herdan:0,S:1}),
   $:()=>({value:''}),fmt:String,Blob,URL:{createObjectURL(){throw Error('Unexpected download')}},
   document:{createElement(){throw Error('Unexpected download')}},setTimeout
  };
  context.$=id=>id==='status'?status:{value:''};
  return vm.runInNewContext(source+';({tableRows,tableCsv,downloadTables})',context);
 };
 for(const name of ['=1+1',"'=1+1",'＋1+1',' \t=1+1','safe\r=1+1']){
  status.textContent='';status.focused=false;
  const api=create(name);
  assert.throws(()=>api.tableCsv(),/Unsafe spreadsheet table cell/);
  assert.equal(api.tableRows().find(row=>row[0]==='document_summary')[2],name);
  api.downloadTables();
  assert.match(status.textContent,/CSV export blocked.*JSON instead/);
  assert.equal(status.focused,true);
  assert.equal(status.tabIndex,-1);
 }
 const safe=create('résumé-東京.csv');
 const csv=safe.tableCsv();
 assert.match(csv,/résumé-東京\.csv/);
 assert.match(csv,/-3/);
 assert.equal(safe.tableRows().find(row=>row[0]==='document_summary')[2],'résumé-東京.csv');
 assert.match(html,/id="downloadTablesJson"/);
 assert.match(html,/\$\('downloadTablesJson'\)\.onclick=downloadTablesJson/);
});


test('non-finite table metrics remain explicitly missing in CSV and JSON, without changing finite values',()=>{
 const start=html.indexOf('function csvEscape(v){');
 const end=html.indexOf('function docDescriptor(',start);
 const riskStart=html.indexOf('function cueCsvRisk(value){');
 const riskEnd=html.indexOf('function cueCsvCell(',riskStart);
 assert.ok(start>0&&end>start&&riskStart>0&&riskEnd>riskStart);
 const source=html.slice(riskStart,riskEnd)+'\n'+html.slice(start,end);
 const marker='not available (non-finite metric)';
 for(const metric of [NaN,Infinity,-Infinity,0,-3.125,42]){
  for(let i=0;i<25;i++){
   const name='0007-Café-東京-'+i+'.md';
   const context={
    sourceDocs:{a:[{id:'a-0007',name,text:'sample'}],b:[]},
    lastA:{W:2,freq:{word:2},collocs:[{term:'two words',count:1,pmi:metric}]},
    lastB:null,lastCompare:false,topEntries:f=>Object.entries(f),
    corpusRows:()=>[],corpusComparison:()=>({similarity:[],keyness:[]}),
    kwicTarget:()=>null,kwic:()=>[],analyze:()=>({W:2,flesch:metric,mattr50:NaN,herdan:0,S:1}),
    $:()=>({value:'',checked:false}),Number,Blob,JSON
   };
   const api=vm.runInNewContext(source+';({tableRows,tableCsv})',context);
   const rows=api.tableRows();
   const colloc=rows.find(row=>row[0]==='collocation');
   const summary=rows.find(row=>row[0]==='document_summary');
   const expected=Number.isFinite(metric)?metric:marker;
   assert.equal(colloc[4],expected);
   assert.equal(summary[4],expected);
   assert.equal(summary[2],name);
   assert.equal(rows.find(row=>row[0]==='frequency')[3],2);
   const json=JSON.parse(JSON.stringify({rows}));
   assert.equal(json.rows.find(row=>row[0]==='collocation')[4],expected);
   assert.equal(json.rows.find(row=>row[0]==='document_summary')[4],expected);
   assert.ok(!json.rows.some(row=>row.some(value=>value===null)));
   const csv=api.tableCsv();
   assert.ok(csv.includes(name));
   assert.ok(csv.includes(String(expected)));
   assert.ok(!csv.includes('NaN')&&!csv.includes('Infinity'));
  }
 }
});


test('table CSV and JSON download failures preserve evidence, clean up resources, and support retry',()=>{
 const start=html.indexOf('function startTableDownload(');
 const end=html.indexOf('function docDescriptor(',start);
 assert.ok(start>0&&end>start);
 const code=html.slice(start,end);
 const rows=[['section','text','item','count','score','left_context','match','right_context'],['document_summary','A','0007-東京.md',2,'not available (non-finite metric)','','','']];
 for(const format of ['CSV','JSON']){
  for(const failure of ['url','append','click','success']){
   const status={textContent:'',tabIndex:0,focused:false,focus(){this.focused=true}};
   const links=[],revoked=[],blobs=[];
   class TestBlob{constructor(parts,options){this.parts=parts;this.options=options;blobs.push(this)}}
   const context={
    Blob:TestBlob,Date,JSON,setTimeout(fn){fn()},
    tableRows:()=>rows,tableCsv:()=>'"safe","0007-東京.md"\r\n',
    $:()=>status,
    URL:{
     createObjectURL(){if(failure==='url')throw Error('blocked URL');return 'blob:synthetic'},
     revokeObjectURL(url){revoked.push(url)}
    },
    document:{
     createElement(){return {href:'',download:'',remove(){const index=links.indexOf(this);if(index>=0)links.splice(index,1)},click(){if(failure==='click')throw Error('blocked click')}}},
     body:{appendChild(link){if(failure==='append')throw Error('blocked append');links.push(link)}}
    }
   };
   const api=vm.runInNewContext(code+';({downloadTables,downloadTablesJson})',context);
   assert.doesNotThrow(()=>format==='CSV'?api.downloadTables():api.downloadTablesJson());
   assert.equal(links.length,0,'no dangling temporary link');
   assert.equal(revoked.length,failure==='url'?0:1,'release created object URL');
   if(failure==='success'){
    assert.match(status.textContent,/Started local/);
    assert.equal(status.focused,false);
    assert.equal(blobs.length,1);
    if(format==='JSON'){
     const payload=JSON.parse(blobs[0].parts.join(''));
     assert.equal(payload.rows[0][2],'0007-東京.md');
     assert.equal(payload.rows[0][4],'not available (non-finite metric)');
    }
   }else{
    assert.match(status.textContent,new RegExp(format+' download could not be started'));
    assert.equal(status.focused,true);
    assert.equal(status.tabIndex,-1);
    assert.doesNotMatch(status.textContent,/0007-東京/);
   }
   assert.equal(rows[1][2],'0007-東京.md');
  }
 }
});
