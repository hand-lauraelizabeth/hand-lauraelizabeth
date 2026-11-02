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
 const handlers={},canceledTimers=[];
 const env={
  // The isolated import-event harness must model the page's pending debounce.
  tm:17,clearTimeout(id){canceledTimers.push(id)},
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
 return {api,env,els,handlers,canceledTimers,get runs(){return runs}};
}
test('rejected external import cancels pending analysis without changing source evidence',()=>{
 const h=harness(true);
 h.els.a.value='Previously accepted source';
 h.env.sourceDocs.a=[{id:'a-7',name:'original.txt',text:'Previously accepted source'}];
 h.handlers['text-lens:import']({detail:{key:'a',name:'bad.txt',size:-1,text:'invalid'}});
 assert.deepEqual(h.canceledTimers,[17]);
 assert.match(h.els.status.textContent,/Import rejected/);
 assert.equal(h.els.status.focused,true);
 assert.equal(h.els.a.value,'Previously accepted source');
 assert.equal(h.env.sourceDocs.a[0].id,'a-7');
});
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
 const names=[
  'reversal'+String.fromCharCode(0x202E)+'txt.md',
  'newline'+String.fromCharCode(10)+'name.md',
  'isolate'+String.fromCharCode(0x2066)+'.txt',
  'bad'+String.fromCharCode(0xD800)+'.md'
 ];
 for(const name of names){
  const h=harness();h.els.a.value='keep';
  const input={files:[file(name,'safe')],value:'chosen'};
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
 const malformed='bad'+String.fromCharCode(0xD800);
 dispatch(malformed,Buffer.byteLength(malformed,'utf8'));
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

test('extracted document keeps derived UTF-8 bytes distinct from original binary bytes',()=>{
 const h=harness(true),text='Café 😀 from PDF';
 const detail={key:'a',name:'sample.pdf',size:encoder.encode(text).byteLength,originalFileBytes:2048,sourceKind:'extracted-text',lastModified:42,text};
 h.handlers['text-lens:import']({detail});
 assert.equal(detail.accepted,true);
 assert.equal(h.els.a.value,text);
 assert.equal(h.env.sourceDocs.a[0].size,encoder.encode(text).byteLength);
 assert.equal(h.env.sourceDocs.a[0].originalFileBytes,2048);
 assert.equal(h.env.sourceDocs.a[0].sourceKind,'extracted-text');
 assert.ok(h.els.fileMetaA.textContent.includes('Extracted text from sample.pdf'));
 assert.equal(h.runs,1);
 const invalid={key:'a',name:'sample.pdf',size:encoder.encode('new').byteLength,originalFileBytes:15000001,sourceKind:'extracted-text',text:'new',accepted:true};
 h.handlers['text-lens:import']({detail:invalid});
 assert.equal(invalid.accepted,false);
 assert.match(h.els.status.textContent,/Import rejected/);
 assert.equal(h.els.status.focused,true);
 assert.equal(h.els.a.value,text);
 assert.equal(h.env.sourceDocs.a[0].originalFileBytes,2048);
 assert.equal(h.runs,1);
});
test('document extraction bridge only changes evidence after validated acceptance',()=>{
 const begin=html.indexOf("q('tl-import-file').addEventListener('change',async function()");
 const end=html.indexOf('</script>',begin);
 assert.ok(begin>0&&end>begin);
 const bridge=html.slice(begin,end);
 assert.ok(bridge.includes("size:new TextEncoder().encode(text).byteLength"));
 assert.ok(bridge.includes('originalFileBytes:file.size'));
 assert.ok(bridge.includes('if(!detail.accepted)return'));
 assert.ok(!bridge.includes('target.value=text'));
 assert.ok(!bridge.includes("target.dispatchEvent(new Event('input'"));
 assert.ok(bridge.includes('bytes.byteLength!==file.size'));
});


function syntheticDocxFixture(marker){
 const entries=[['[Content_Types].xml','<Types/>'],['_rels/.rels','<Relationships/>'],['word/document.xml','<w:document>'+marker+'</w:document>']];
 const parts=[],directory=[];let offset=0;
 for(const [name,body] of entries){
  const n=Buffer.from(name),data=Buffer.from(body),local=Buffer.alloc(30),central=Buffer.alloc(46);
  local.writeUInt32LE(0x04034b50,0);local.writeUInt32LE(data.length,18);local.writeUInt32LE(data.length,22);local.writeUInt16LE(n.length,26);
  central.writeUInt32LE(0x02014b50,0);central.writeUInt32LE(data.length,20);central.writeUInt32LE(data.length,24);central.writeUInt16LE(n.length,28);central.writeUInt32LE(offset,42);
  parts.push(local,n,data);directory.push(central,n);offset+=local.length+n.length+data.length;
 }
 const centralBytes=Buffer.concat(directory),end=Buffer.alloc(22);
 end.writeUInt32LE(0x06054b50,0);end.writeUInt16LE(entries.length,8);end.writeUInt16LE(entries.length,10);
 end.writeUInt32LE(centralBytes.length,12);end.writeUInt32LE(offset,16);
 return Buffer.concat([...parts,centralBytes,end]);
}
function documentImportHarness(){
 const begin=html.indexOf("<script>(function(){const r=document.getElementById('leh-text-lens-app');if(!r||!['tl-import-file'");
 const end=html.indexOf('</script>',begin);
 assert.ok(begin>0&&end>begin,'Document import bridge exists');
 const script=html.slice(begin+8,end);
 const events=[],handlers={};
 const status={textContent:'',focused:false,focus(){this.focused=true}};
 const input={files:[],value:'selected',addEventListener(type,handler){handlers[type]=handler}};
 const side={value:'a'};
 const cmp={checked:false,dispatchEvent(){}};
 const root={
  querySelector(selector){return ({'tl-import-file':input,'tl-import-side':side,'tl-import-status':status,cmp})[selector.slice(1)]||null},
  dispatchEvent(event){events.push(event.detail);event.detail.accepted=true}
 };
 const window={
  mammoth:{async extractRawText(){return {value:'DOCX extracted evidence'}}},
  pdfjsLib:{
   GlobalWorkerOptions:{},
   getDocument({data}){return {promise:Promise.resolve({
    numPages:1,
    async getPage(){return {async getTextContent(){return {items:[{str:'PDF evidence '+String.fromCharCode(data[5])}]}}}}
   })}}
  }
 };
 const loads=[],queuedLoads=[],removedScripts=[],pendingTimers=new Map();let timerId=0;let failLocal=false,overridePdf=null,overrideLoadingTask=null,deferLocal=false,loadingTaskStarted=0;
 const completeLocalLoad=script=>{
   if(failLocal){script.onerror();return}
   if(script.src.endsWith('/mammoth.browser.min.js'))window.mammoth={async extractRawText(){return {value:'DOCX extracted evidence'}}};
   else if(script.src.endsWith('/pdf.min.js'))window.pdfjsLib={
    GlobalWorkerOptions:{},
    getDocument({data}){loadingTaskStarted++;return overrideLoadingTask||{promise:Promise.resolve(overridePdf||{numPages:1,
     async getPage(){return {async getTextContent(){return {items:[{str:'PDF evidence '+String.fromCharCode(data[5])}]}}}}
    })}}
   };
   else throw Error('Unexpected local asset: '+script.src);
   script.onload();
 };
 const document={location:{protocol:'https:',origin:'https://example.test',href:'https://example.test/projects/text-lens/text-lens.html'},
  getElementById(){return root},
  createElement(type){assert.equal(type,'script');return {src:'',onload:null,onerror:null,remove(){removedScripts.push(this.src)}}},
  head:{appendChild(script){
   loads.push(script.src);
   if(deferLocal)queuedLoads.push(script);
   else completeLocalLoad(script);
  }}
 };
 const context={document,window,URL,TextEncoder,TextDecoder,DataView,Uint8Array,ArrayBuffer,Number,
   setTimeout(fn){const id=++timerId;pendingTimers.set(id,fn);return id},clearTimeout(id){pendingTimers.delete(id)},
  CustomEvent:class{constructor(type,{detail}){this.type=type;this.detail=detail}},
  Event:class{constructor(type){this.type=type}}
 };
 vm.runInNewContext(script,context);
 const bytes=raw=>{const b=Buffer.from(raw);return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)};
 const file=(name,raw,read)=>{const value=/\.docx$/i.test(name)&&typeof raw==='string'&&raw.startsWith('PK\x03\x04')?syntheticDocxFixture(raw):Buffer.from(raw);const data=value.buffer.slice(value.byteOffset,value.byteOffset+value.byteLength);return {name,size:data.byteLength,lastModified:42,arrayBuffer:read||(async()=>data)}};
 return {events,handlers,input,side,status,window,file,bytes,loads,document,removedScripts,getPendingTimers(){return pendingTimers.size},flushTimers(){const tasks=[...pendingTimers.values()];pendingTimers.clear();tasks.forEach(fn=>fn())},setLocalFailure(value){failLocal=value},setPdfDocument(value){overridePdf=value},setPdfLoadingTask(value){overrideLoadingTask=value},getLoadingTaskStarts(){return loadingTaskStarted},setLocalDelay(value){deferLocal=value},flushLocalLoads(){queuedLoads.splice(0).forEach(completeLocalLoad)}};
}
test('document bridge rejects extension/signature mismatches before invoking extraction libraries',async()=>{
 const h=documentImportHarness();
 let calls=0;
 h.window.pdfjsLib.getDocument=()=>{calls++;throw Error('unexpected PDF parse')};
 h.window.mammoth.extractRawText=async()=>{calls++;throw Error('unexpected DOCX parse')};
 for(const [name,raw] of [['mismatch.pdf','PK\x03\x04fake'],['mismatch.docx','%PDF-fake'],['empty.pdf','abcd']]){
  h.input.files=[h.file(name,raw)];h.input.value='selected';h.status.focused=false;
  await h.handlers.change.call(h.input);
  assert.match(h.status.textContent,/signature does not match/);
  assert.equal(h.status.focused,true);
  assert.equal(h.input.value,'');
 }
 assert.equal(calls,0);
 assert.equal(h.events.length,0);
});
test('document bridge accepts matching PDF and DOCX headers and retains original byte provenance',async()=>{
 const h=documentImportHarness();
 for(const [name,raw,expected] of [['good.pdf','%PDF-A','PDF evidence A'],['good.docx','PK\x03\x04sample','DOCX extracted evidence']]){
  h.input.files=[h.file(name,raw)];h.input.value='selected';
  await h.handlers.change.call(h.input);
  const d=h.events.at(-1);
  assert.equal(d.name,name);assert.equal(d.text,expected);
  assert.equal(d.originalFileBytes,h.file(name,raw).size);
  assert.equal(d.size,new TextEncoder().encode(expected).byteLength);
  assert.match(h.status.textContent,/Imported extracted text/);
 }
 assert.equal(h.events.length,2);
});
test('stale document extraction cannot overwrite a newer accepted document or its status',async()=>{
 const h=documentImportHarness();
 let resolveOld;
 const old=h.file('old.pdf','%PDF-A',()=>new Promise(resolve=>{resolveOld=resolve}));
 h.input.files=[old];h.input.value='selected';h.side.value='a';
 const first=h.handlers.change.call(h.input);
 assert.equal(h.input.value,'','same file can be reselected while pending');
 h.input.files=[h.file('new.pdf','%PDF-B')];h.input.value='selected';h.side.value='b';
 await h.handlers.change.call(h.input);
 assert.equal(h.events.length,1);
 assert.equal(h.events[0].name,'new.pdf');
 assert.equal(h.events[0].key,'b');
 const latest=h.status.textContent;
 resolveOld(h.bytes('%PDF-A'));await first;
 assert.equal(h.events.length,1);
 assert.equal(h.status.textContent,latest);
});

test('PDF.js loading task is destroyed when parsing rejects before a document proxy exists',async()=>{
 const h=documentImportHarness();let taskDestroyed=0;
 h.setPdfLoadingTask({
  promise:new Promise((_,reject)=>setImmediate(()=>reject(Error('synthetic corrupt PDF')))),
  async destroy(){taskDestroyed++}
 });
 h.input.files=[h.file('corrupt.pdf','%PDF-A')];h.input.value='selected';
 await h.handlers.change.call(h.input);
 assert.equal(taskDestroyed,1,'rejected parser must release its loading task and worker');
 assert.equal(h.events.length,0,'rejected document must not replace accepted evidence');
 assert.match(h.status.textContent,/synthetic corrupt PDF/);
 assert.equal(h.status.focused,true);
});
test('successful PDF.js loading task uses one task-level cleanup, not double proxy destruction',async()=>{
 const h=documentImportHarness();let taskDestroyed=0,proxyDestroyed=0;
 const pdf={numPages:1,async getPage(){return {async getTextContent(){return {items:[{str:'synthetic page'}]}}}},
  async destroy(){proxyDestroyed++}};
 h.setPdfLoadingTask({promise:Promise.resolve(pdf),async destroy(){taskDestroyed++}});
 h.input.files=[h.file('valid.pdf','%PDF-A')];h.input.value='selected';
 await h.handlers.change.call(h.input);
 assert.equal(h.events.length,1);
 assert.equal(h.events[0].text,'synthetic page');
 assert.equal(taskDestroyed,1);
 assert.equal(proxyDestroyed,0,'loading task owns worker and document teardown');
});
test('superseded PDF loading task is released without replacing the newer document',async()=>{
 const h=documentImportHarness();let resolveOld,taskDestroyed=0;
 h.setPdfLoadingTask({promise:new Promise(resolve=>{resolveOld=resolve}),
  async destroy(){taskDestroyed++}});
 h.input.files=[h.file('stale.pdf','%PDF-A')];h.input.value='selected';
 const stale=h.handlers.change.call(h.input);
 for(let attempt=0;attempt<10&&!h.getLoadingTaskStarts();attempt++)
  await new Promise(resolve=>setImmediate(resolve));
 assert.equal(h.getLoadingTaskStarts(),1,'stale PDF loading task must exist before replacement');
 h.input.files=[h.file('current.docx','PK\x03\x04current')];h.input.value='selected';
 await h.handlers.change.call(h.input);
 assert.equal(h.events.length,1);
 assert.equal(h.events[0].name,'current.docx');
 const status=h.status.textContent;
 resolveOld({numPages:1,async getPage(){throw Error('obsolete document traversed')}});
 await stale;
 assert.equal(taskDestroyed,1);
 assert.equal(h.events.length,1);
 assert.equal(h.status.textContent,status);
});
test('PDF import rejects invalid page counts before traversal and destroys the document',async()=>{
 for(const count of [0,501,NaN]){
  const h=documentImportHarness();let reads=0,destroyed=0;
  h.setPdfDocument({numPages:count,async getPage(){reads++;throw Error('should not traverse')},
   async destroy(){destroyed++}});
  h.input.files=[h.file('oversized.pdf','%PDF-A')];
  await h.handlers.change.call(h.input);
  assert.equal(reads,0);
  assert.equal(destroyed,1);
  assert.equal(h.events.length,0);
  assert.match(h.status.textContent,/PDF page count must be between 1 and 500/);
  assert.equal(h.status.focused,true);
 }
});
test('PDF import bounds extracted text during traversal, preserving evidence on rejection',async()=>{
 const h=documentImportHarness();let pagesRead=0,destroyed=0;
 h.setPdfDocument({numPages:3,async getPage(i){
  pagesRead++;return {async getTextContent(){return {items:[{str:i===1?'a'.repeat(399999):'b'}]}}}
 },async destroy(){destroyed++}});
 h.input.files=[h.file('too-long.pdf','%PDF-A')];
 await h.handlers.change.call(h.input);
 assert.equal(pagesRead,2,'stop before processing the third page');
 assert.equal(destroyed,1);
 assert.equal(h.events.length,0);
 assert.match(h.status.textContent,/400,000-character field limit/);
 assert.equal(h.status.focused,true);
 assert.doesNotMatch(h.status.textContent,/a{20}/,'no extracted content in error');
});
test('PDF import retains exact Unicode page text and releases the parsed document',async()=>{
 const h=documentImportHarness();let destroyed=0;
 h.setPdfDocument({numPages:2,async getPage(i){
  return {async getTextContent(){return {items:[{str:i===1?'東京':'Café'},{str:'source'}]}}}
 },async destroy(){destroyed++}});
 h.input.files=[h.file('unicode.pdf','%PDF-A')];
 await h.handlers.change.call(h.input);
 assert.equal(destroyed,1);
 assert.equal(h.events.length,1);
 assert.equal(h.events[0].text,'東京 source\\n\\nCafé source'.replace(/\\n/g,'\n'));
 assert.equal(h.events[0].size,new TextEncoder().encode(h.events[0].text).byteLength);
 assert.match(h.status.textContent,/Imported extracted text/);
});

test('document extraction loads only same-origin scripts and a same-origin PDF worker',async()=>{
 const h=documentImportHarness();
 for(const [name,raw] of [['same.pdf','%PDF-A'],['same.docx','PK\x03\x04sample']]){
  h.input.files=[h.file(name,raw)];h.input.value='selected';
  await h.handlers.change.call(h.input);
 }
 assert.equal(h.events.length,2);
 assert.deepEqual(h.loads,[
  'https://example.test/projects/text-lens/vendor/pdf.min.js',
  'https://example.test/projects/text-lens/vendor/mammoth.browser.min.js'
 ]);
 assert.equal(h.window.pdfjsLib.GlobalWorkerOptions.workerSrc,
  'https://example.test/projects/text-lens/vendor/pdf.worker.min.js');
 assert.ok(h.loads.every(src=>new URL(src).origin==='https://example.test'));
});
test('repeated PDF and DOCX imports reuse only successfully loaded same-origin parser scripts',async()=>{
 const h=documentImportHarness();
 for(const [name,raw] of [
  ['first.pdf','%PDF-A'],['second.pdf','%PDF-B'],
  ['first.docx','PK\x03\x04one'],['second.docx','PK\x03\x04two']
 ]){
  h.input.files=[h.file(name,raw)];h.input.value='selected';
  await h.handlers.change.call(h.input);
 }
 assert.equal(h.events.length,4,'all four synthetic documents import');
 assert.deepEqual(h.events.map(e=>e.name),['first.pdf','second.pdf','first.docx','second.docx']);
 assert.deepEqual(h.loads,[
  'https://example.test/projects/text-lens/vendor/pdf.min.js',
  'https://example.test/projects/text-lens/vendor/mammoth.browser.min.js'
 ],'each reviewed same-origin parser executes only once');
 assert.equal(h.window.pdfjsLib.GlobalWorkerOptions.workerSrc,
  'https://example.test/projects/text-lens/vendor/pdf.worker.min.js');
});
test('overlapping document selections share one pending same-origin parser load',async()=>{
 const h=documentImportHarness();h.setLocalDelay(true);
 h.input.files=[h.file('stale.docx','PK\x03\x04stale')];h.input.value='selected';
 const stale=h.handlers.change.call(h.input);
 await new Promise(resolve=>setImmediate(resolve));
 h.input.files=[h.file('current.docx','PK\x03\x04current')];h.input.value='selected';
 const current=h.handlers.change.call(h.input);
 await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(h.loads,['https://example.test/projects/text-lens/vendor/mammoth.browser.min.js'],
  'two overlapping selections must not execute the parser script twice');
 h.flushLocalLoads();
 await Promise.all([stale,current]);
 assert.equal(h.events.length,1,'obsolete import must not overwrite the latest selection');
 assert.equal(h.events[0].name,'current.docx');
 assert.match(h.status.textContent,/Imported extracted text/);
});
test('failed local parser load is not cached and can be retried without trusting preloaded globals',async()=>{
 const h=documentImportHarness();h.setLocalFailure(true);
 h.window.mammoth={async extractRawText(){throw Error('unverified global must never execute')}};
 h.input.files=[h.file('first.docx','PK\x03\x04first')];
 await h.handlers.change.call(h.input);
 assert.equal(h.events.length,0);
 assert.match(h.status.textContent,/Reviewed local extraction library is not installed/);
 assert.equal(h.status.focused,true);
 h.setLocalFailure(false);h.status.focused=false;
 h.input.files=[h.file('retry.docx','PK\x03\x04retry')];
 await h.handlers.change.call(h.input);
 assert.equal(h.events.length,1);
 assert.equal(h.events[0].name,'retry.docx');
 assert.match(h.status.textContent,/Imported extracted text/);
 assert.deepEqual(h.loads,[
  'https://example.test/projects/text-lens/vendor/mammoth.browser.min.js',
  'https://example.test/projects/text-lens/vendor/mammoth.browser.min.js'
 ],'a failed load is retried from the same origin');
});

test('missing local extraction libraries fail closed even with a preloaded global',async()=>{
 const h=documentImportHarness();h.setLocalFailure(true);
 h.window.mammoth={async extractRawText(){throw Error('Must not use preloaded global')}};
 h.input.files=[h.file('missing.docx','PK\x03\x04sample')];h.input.value='selected';
 await h.handlers.change.call(h.input);
 assert.equal(h.events.length,0);
 assert.match(h.status.textContent,/Reviewed local extraction library is not installed/);
 assert.equal(h.status.focused,true);
 assert.deepEqual(h.loads,['https://example.test/projects/text-lens/vendor/mammoth.browser.min.js']);
});
test('non-HTTP document contexts fail before loading any script',async()=>{
 const h=documentImportHarness();
 h.document.location={protocol:'file:',origin:'null',href:'file:///tmp/text-lens.html'};
 h.input.files=[h.file('local.pdf','%PDF-A')];h.input.value='selected';
 await h.handlers.change.call(h.input);
 assert.equal(h.events.length,0);
 assert.equal(h.loads.length,0);
 assert.ok(h.status.textContent.includes('requires an HTTP(S) page'));
 assert.equal(h.status.focused,true);
});
test('document import contains no third-party CDN execution path',()=>{
 const start=html.indexOf("<script>(function(){const r=document.getElementById('leh-text-lens-app');if(!r||!['tl-import-file'");
 const end=html.indexOf('</script>',start);
 const bridge=html.slice(start,end);
 assert.ok(bridge.includes("loadLocal('pdf.min.js'"));
 assert.ok(bridge.includes("loadLocal('mammoth.browser.min.js'"));
 assert.ok(bridge.includes("localAsset('pdf.worker.min.js')"));
 assert.ok(!bridge.includes('https://')&&!bridge.includes('http://'));
 assert.ok(!['cdn.','jsdelivr','cdnjs','unpkg'].some(host=>bridge.includes(host)));
});


test('evidence CSV, exact evidence JSON and source-free analysis JSON recover from blocked downloads',()=>{
 const slice=(a,b)=>{const start=html.indexOf(a),end=html.indexOf(b,start);assert.ok(start>=0&&end>start);return html.slice(start,end)};
 const script=slice('function startTableDownload(','function downloadTables(){')+'\n'+
  slice('function cueCsvCell(','let evidenceRows=')+'\n'+
  slice('function downloadAnalysis(){','async function copySummary()');
 const source={side:'a',source:'0007-Café-東京.md',term:'signal',polarity:'thematic',
  categories:['theme'],adjustments:[],sentence:1,line:1,char:1,word:1,percent:12.5,
  passage:'Synthetic source passage',voice:'prose',speaker:'',speakerMention:'',
  speakerStatus:'unresolved',actorRule:'none',aspect:'',aspectRule:''};
 for(const mode of ['CSV','Evidence JSON','Analysis JSON']){
  for(const failure of ['url','append','click','success']){
   const links=[],revoked=[],blobs=[],status={textContent:'',tabIndex:0,focused:false,focus(){this.focused=true}};
   class TestBlob{constructor(parts,options){this.parts=parts;this.options=options;blobs.push(this)}}
   const ctx={
    Blob:TestBlob,Date,JSON,Number,Error,Set,setTimeout(fn){fn()},
    URL:{createObjectURL(){if(failure==='url')throw Error('blocked URL');return 'blob:synthetic'},
     revokeObjectURL(url){revoked.push(url)}},
    document:{createElement(){return {href:'',download:'',click(){if(failure==='click')throw Error('blocked click')},
     remove(){const index=links.indexOf(this);if(index>=0)links.splice(index,1)}}},
     body:{appendChild(link){if(failure==='append')throw Error('blocked append');links.push(link)}}},
    $(id){return id==='status'?status:{value:'',checked:false}},
    evidenceFiltered:()=>[source],cueCsvRisk:()=>false,
    sourceDocs:{a:[{id:'a-0007',name:source.source,text:'Original local source not for export'}],b:[]},
    sourceFiles:{a:[source.source],b:[]},lastA:{W:2},lastB:null,lastCompare:false,
    customRefIds:new Set(),buildCorpusSetup:()=>({}),publicResult:()=>({words:2}),
    publicCorpusComparison:()=>({}),comparisonExport:()=>({}),analyze:()=>({W:2})
   };
   const api=vm.runInNewContext(script+';({exportEvidence,downloadEvidenceJson,downloadAnalysis})',ctx);
   assert.doesNotThrow(()=>mode==='CSV'?api.exportEvidence():mode==='Evidence JSON'?api.downloadEvidenceJson():api.downloadAnalysis());
   assert.equal(links.length,0,mode+' '+failure+' must not retain an anchor');
   assert.equal(revoked.length,failure==='url'?0:1,mode+' '+failure+' must release any URL');
   assert.equal(blobs.length,1);
   if(failure==='success'){
    assert.match(status.textContent,/Started local/);
    assert.equal(status.focused,false);
    if(mode==='CSV'){
     assert.equal(blobs[0].parts[0],'\ufeff');
     assert.ok(blobs[0].parts[1].includes(source.source));
    }else{
     const payload=JSON.parse(blobs[0].parts.join(''));
     if(mode==='Evidence JSON'){
      assert.equal(payload.rows[0].source,source.source);
      assert.equal(payload.rows[0].passage,source.passage);
     }else{
      assert.equal(payload.source_files.text_a[0],source.source);
      assert.ok(!JSON.stringify(payload).includes('Original local source not for export'));
     }
    }
   }else{
    assert.match(status.textContent,new RegExp(mode+' download could not be started'));
    assert.equal(status.tabIndex,-1);
    assert.equal(status.focused,true);
    assert.doesNotMatch(status.textContent,/Café|東京|Synthetic source passage/);
   }
   assert.equal(source.source,'0007-Café-東京.md');
  }
 }
});


test('document bridge times out stalled same-origin parser and retries without replacing accepted evidence',async()=>{
 const h=documentImportHarness();h.setLocalDelay(true);
 h.input.files=[h.file('stalled.docx','PK\x03\x04stalled')];
 const pending=h.handlers.change.call(h.input);
 for(let i=0;i<10&&!h.getPendingTimers();i++)await new Promise(resolve=>setImmediate(resolve));
 assert.equal(h.getPendingTimers(),1,'stalled loader must have one bounded timeout');
 h.flushTimers();await pending;
 assert.match(h.status.textContent,/timed out after 15 seconds/);
 assert.equal(h.events.length,0);
 assert.equal(h.status.focused,true);
 assert.equal(h.removedScripts.length,1);
 h.setLocalDelay(false);
 h.input.files=[h.file('retry.docx','PK\x03\x04retry')];
 await h.handlers.change.call(h.input);
 assert.equal(h.events.length,1);
 assert.equal(h.events[0].name,'retry.docx');
 assert.equal(h.getPendingTimers(),0,'successful load clears timer');
 assert.equal(h.removedScripts.length,2,'both loader elements are removed');
});
test('document bridge recovers from blocked parser insertion and retry remains local',async()=>{
 const h=documentImportHarness();
 const original=h.document.head.appendChild;
 h.document.head.appendChild=()=>{throw Error('synthetic DOM insertion blocked')};
 h.input.files=[h.file('blocked.pdf','%PDF-blocked')];
 await h.handlers.change.call(h.input);
 assert.match(h.status.textContent,/could not be loaded/);
 assert.equal(h.events.length,0);
 assert.equal(h.removedScripts.length,1);
 assert.equal(h.getPendingTimers(),0);
 h.document.head.appendChild=original;
 h.input.files=[h.file('recovered.pdf','%PDF-recovered')];
 await h.handlers.change.call(h.input);
 assert.equal(h.events.length,1);
 assert.equal(h.events[0].name,'recovered.pdf');
 assert.equal(h.removedScripts.length,2);
});
test('document bridge catches parser global initialization errors instead of leaving import pending',async()=>{
 const h=documentImportHarness();let current=h.window.mammoth,reads=0;
 Object.defineProperty(h.window,'mammoth',{configurable:true,get(){reads++;if(reads>1)throw Error('synthetic getter failure');return current},set(v){current=v}});
 h.input.files=[h.file('bad.docx','PK\x03\x04bad')];
 await h.handlers.change.call(h.input);
 assert.match(h.status.textContent,/could not initialize/);
 assert.equal(h.events.length,0);
 assert.equal(h.getPendingTimers(),0);
 assert.equal(h.removedScripts.length,1);
});

test('unsafe evidence CSV is blocked while exact JSON preserves synthetic formula-like source values',()=>{
 const slice=(a,b)=>{const i=html.indexOf(a),j=html.indexOf(b,i);assert.ok(i>=0&&j>i);return html.slice(i,j)};
 const script=slice('function startTableDownload(','function downloadTables(){')+'\n'+slice('function cueCsvCell(','let evidenceRows=');
 const status={textContent:'',focused:false,focus(){this.focused=true}};
 const row={side:'a',source:'=HYPERLINK("https://invalid.example")',term:'safe',polarity:'thematic',
  categories:[],adjustments:[],sentence:1,line:1,char:1,word:1,percent:1,
  passage:'synthetic',voice:'prose',speaker:'',speakerMention:'',speakerStatus:'',
  actorRule:'',aspect:'',aspectRule:''};
 const downloads=[];
 const ctx={Date,JSON,Number,Error,Blob:class{constructor(parts){this.parts=parts;downloads.push(this)}},
  URL:{createObjectURL(){return 'blob:test'},revokeObjectURL(){}},
  document:{createElement(){return {click(){},remove(){}}},body:{appendChild(){}}},
  setTimeout(fn){fn()},$(id){return status},evidenceFiltered:()=>[row],
  cueCsvRisk:value=>String(value).startsWith('=')};
 const api=vm.runInNewContext(script+';({exportEvidence,downloadEvidenceJson})',ctx);
 api.exportEvidence();assert.match(status.textContent,/CSV export blocked/);assert.equal(status.focused,true);
 assert.equal(downloads.length,0);
 api.downloadEvidenceJson();assert.equal(downloads.length,1);
 assert.equal(JSON.parse(downloads[0].parts.join('')).rows[0].source,row.source);
});

test('DOCX preflight rejects forged ZIP headers before loading extraction code',async()=>{
 const h=documentImportHarness(),bad=Buffer.from('PK\x03\x04not-an-archive','binary');
 h.input.files=[{name:'forged.docx',size:bad.length,lastModified:42,async arrayBuffer(){return bad.buffer.slice(bad.byteOffset,bad.byteOffset+bad.length)}}];
 await h.handlers.change.call(h.input);
 assert.match(h.status.textContent,/Invalid or unsupported DOCX ZIP package/);
 assert.equal(h.events.length,0);assert.equal(h.loads.length,0);
});
test('DOCX preflight rejects declared decompression bombs before loading parser',async()=>{
 const h=documentImportHarness(),raw=syntheticDocxFixture('safe');
 const central=raw.indexOf(Buffer.from([0x50,0x4b,0x01,0x02]));
 assert.ok(central>0);raw.writeUInt32LE(40000000,central+20);raw.writeUInt32LE(40000000,central+24);
 h.input.files=[{name:'bomb.docx',size:raw.length,lastModified:42,async arrayBuffer(){return raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.length)}}];
 await h.handlers.change.call(h.input);
 assert.match(h.status.textContent,/expanded contents exceed/);
 assert.equal(h.events.length,0);assert.equal(h.loads.length,0);
});
test('DOCX preflight rejects non-Word ZIP packages before loading parser',async()=>{
 const h=documentImportHarness(),raw=syntheticDocxFixture('safe');
 const target=Buffer.from('word/document.xml'),idx=raw.indexOf(target);
 assert.ok(idx>0);raw.write('word/document.zzz',idx,'utf8');
 h.input.files=[{name:'renamed.zip.docx',size:raw.length,lastModified:42,async arrayBuffer(){return raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.length)}}];
 await h.handlers.change.call(h.input);
 assert.match(h.status.textContent,/Invalid or unsupported DOCX ZIP package/);
 assert.equal(h.events.length,0);assert.equal(h.loads.length,0);
});
