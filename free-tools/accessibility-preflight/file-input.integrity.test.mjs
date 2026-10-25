import assert from 'node:assert/strict';
import test from 'node:test';
import {bindHTMLFile} from './file-input.mjs';

const encoder=new TextEncoder();
const bytes=text=>encoder.encode(text);
const bufferFor=data=>data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength);
const file=(name,data,declared=data.byteLength)=>({
 name,size:declared,arrayBuffer:async()=>bufferFor(data)
});
function harness(){
 const control=()=>({
  listeners:{},value:'',textContent:'',focused:false,files:[],
  addEventListener(name,callback){this.listeners[name]=callback;},
  fire(name){return this.listeners[name]?.();},
  focus(){this.focused=true;}
 });
 const input=control(),target=control(),status=control();
 target.value='Earlier source';
 bindHTMLFile(input,target,status);
 return {input,target,status};
}
test('valid UTF-8 file retains exact Unicode, CRLF and original text',async()=>{
 const {input,target,status}=harness();
 const source='<h1>Évidence 🧾</h1>\r\n<p>line</p>';
 input.files=[file('sample.HTML',bytes(source))];
 await input.fire('change');
 assert.equal(target.value,source);
 assert.match(status.textContent,/HTML loaded locally/);
 assert.equal(input.value,'');
});
test('file-size metadata is validated before any read',async()=>{
 for(const invalid of [undefined,NaN,Infinity,-1,0,1.5,2_000_001]){
  const {input,target,status}=harness();
  let read=false;
  input.files=[{name:'sample.html',size:invalid,arrayBuffer:async()=>{read=true;return bufferFor(bytes('test'));}}];
  await input.fire('change');
  assert.equal(read,false);
  assert.equal(target.value,'Earlier source');
  assert.match(status.textContent,/File rejected/);
  assert.equal(status.focused,true);
 }
});
test('short and long reads are rejected, preserving prior source',async()=>{
 const data=bytes('<p>Exact</p>');
 for(const declared of [data.byteLength-1,data.byteLength+1]){
  const {input,target,status}=harness();
  input.files=[file('sample.htm',data,declared)];
  await input.fire('change');
  assert.equal(target.value,'Earlier source');
  assert.match(status.textContent,/byte count does not match/);
  assert.equal(status.focused,true);
  assert.equal(input.value,'');
 }
});
test('non-ArrayBuffer results fail closed',async()=>{
 for(const returned of [null,'text',bytes('test'),{byteLength:4}]){
  const {input,target,status}=harness();
  input.files=[{name:'sample.html',size:4,arrayBuffer:async()=>returned}];
  await input.fire('change');
  assert.equal(target.value,'Earlier source');
  assert.match(status.textContent,/did not return an ArrayBuffer/);
 }
});
test('malformed UTF-8 and wrong extension do not replace source',async()=>{
 for(const candidate of [file('sample.html',Uint8Array.from([0xc3,0x28])),file('sample.svg',bytes('text'))]){
  const {input,target,status}=harness();
  input.files=[candidate];
  await input.fire('change');
  assert.equal(target.value,'Earlier source');
  assert.match(status.textContent,/File rejected/);
  assert.equal(status.focused,true);
 }
});
test('typing during pending read wins over delayed file completion',async()=>{
 const {input,target,status}=harness();
 let finish;
 const pending=new Promise(resolve=>finish=resolve);
 input.files=[{name:'delayed.html',size:4,arrayBuffer:()=>pending}];
 const read=input.fire('change');
 target.value='Manual edit';
 await target.fire('input');
 finish(bufferFor(bytes('test')));
 await read;
 assert.equal(target.value,'Manual edit');
 assert.equal(status.textContent,'');
});
test('later valid selection wins over an earlier delayed read',async()=>{
 const {input,target,status}=harness();
 let finish;
 const pending=new Promise(resolve=>finish=resolve);
 input.files=[{name:'older.html',size:3,arrayBuffer:()=>pending}];
 const older=input.fire('change');
 input.files=[file('newer.html',bytes('new'))];
 await input.fire('change');
 finish(bufferFor(bytes('old')));
 await older;
 assert.equal(target.value,'new');
 assert.match(status.textContent,/HTML loaded locally/);
});
test('a valid selection succeeds after a rejected mismatch',async()=>{
 const {input,target,status}=harness();
 const data=bytes('<h1>Ready</h1>');
 input.files=[file('first.html',data,data.byteLength+1)];
 await input.fire('change');
 assert.match(status.textContent,/File rejected/);
 input.files=[file('second.html',data)];
 await input.fire('change');
 assert.equal(target.value,'<h1>Ready</h1>');
 assert.match(status.textContent,/HTML loaded locally/);
});

test('BOM-only, whitespace-only and NUL-containing files fail closed',async()=>{
 const cases=[
  {name:'bom.html',data:Uint8Array.from([0xef,0xbb,0xbf]),message:/no text to analyze/},
  {name:'whitespace.htm',data:bytes(' \r\n\t '),message:/no text to analyze/},
  {name:'nul.html',data:bytes('<h1>Before\\0After</h1>'.replace('\\0','\u0000')),message:/NUL character/}
 ];
 for(const candidate of cases){
  const {input,target,status}=harness();
  input.files=[file(candidate.name,candidate.data)];
  await input.fire('change');
  assert.equal(target.value,'Earlier source',candidate.name);
  assert.match(status.textContent,candidate.message,candidate.name);
  assert.equal(status.focused,true,candidate.name);
  assert.equal(input.value,'',candidate.name);
 }
});
test('valid HTML with UTF-8 BOM still imports and preserves its decoded content',async()=>{
 const {input,target,status}=harness();
 const source='<h1>Évidence 🧾</h1>\r\n<p>ok</p>';
 const data=bytes(source);
 const withBOM=Uint8Array.from([0xef,0xbb,0xbf,...data]);
 input.files=[file('good.html',withBOM)];
 await input.fire('change');
 assert.equal(target.value,source);
 assert.match(status.textContent,/HTML loaded locally/);
});
test('valid file recovers after empty or NUL input',async()=>{
 const {input,target,status}=harness();
 for(const data of [bytes(' \n '),bytes('<p>\u0000</p>')]){
  input.files=[file('bad.html',data)];
  await input.fire('change');
  assert.match(status.textContent,/File rejected/);
  assert.equal(target.value,'Earlier source');
 }
 input.files=[file('good.html',bytes('<p>Recovered</p>'))];
 await input.fire('change');
 assert.equal(target.value,'<p>Recovered</p>');
 assert.match(status.textContent,/HTML loaded locally/);
});
