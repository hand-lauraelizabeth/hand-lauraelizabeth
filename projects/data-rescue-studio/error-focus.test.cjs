'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
const reconcile=fs.readFileSync(path.join(__dirname,'reconcile-ui.js'),'utf8');
function mock(){
 const all=new Map();
 const get=id=>{
  if(!all.has(id))all.set(id,{id,value:'',disabled:false,checked:false,files:[],options:[{value:''}],textContent:'',className:'',focusCount:0,handlers:{},
   focus(){this.focusCount++},addEventListener(k,fn){this.handlers[k]=fn},replaceChildren(){},append(){},click(){},remove(){}});
  return all.get(id);
 };
 return {get,document:{getElementById:get,createTextNode:text=>({textContent:text}),
  createElement:tag=>({tag,textContent:'',value:'',append(){},replaceChildren(){}}),body:{append(){}}}};
}
test('import errors have programmatically focusable, visibly outlined summaries',()=>{
 assert.match(html,/<p id="status"[^>]*tabindex="-1"/);
 assert.match(html,/<p id="compareStatus"[^>]*tabindex="-1"/);
 assert.match(html,/#status:focus,#compareStatus:focus\{outline:3px/);
 assert.match(html,/if\(error\)node\.focus\(\)/);
 assert.match(reconcile,/if \(error\) node\.focus\(\)/);
});
test('primary import errors focus the descriptive status',async()=>{
 const {get,document}=mock();
 const window={DataRescue:{MAX_BYTES:5000000,parseDelimited(){return {rows:[],normalizedHeaders:[],warnings:[]}}},
  DataRescueHistoryUI:{onClear(){},onLoad(){},recordExport(){}},DataRescueCompareUI:{setPrimary(){}},
  DataRescueFileReader:{read:async()=>{throw Error('invalid UTF-8')}}};
 const source=html.match(/<script>\s*([\s\S]*?)<\/script><\/body>/)?.[1];
 assert.ok(source);
 vm.runInNewContext(source,{window,document,URL:{createObjectURL(){return 'blob:test'},revokeObjectURL(){}},Blob:class{},setTimeout(){}});
 get('file').files=[{name:'invalid.exe',size:1}];await get('file').handlers.change();
 assert.equal(get('status').focusCount,1);assert.match(get('status').textContent,/\.csv or \.tsv/);
 get('file').files=[{name:'too-large.csv',size:5000001}];await get('file').handlers.change();
 assert.equal(get('status').focusCount,2);
 get('file').files=[{name:'bad.csv',size:5}];await get('file').handlers.change();
 assert.equal(get('status').focusCount,3);assert.match(get('status').textContent,/invalid UTF-8/);
});
test('secondary errors focus; successful load does not steal focus',async()=>{
 const {get,document}=mock();
 const window={DataRescue:{MAX_BYTES:5000000,parseDelimited(){return {rows:[],normalizedHeaders:[],warnings:[]}}},DataRescueProvenance:{}};
 vm.runInNewContext(reconcile,{window,document});
 window.DataRescueCompareUI.setPrimary({normalizedHeaders:['id'],rows:[]},'first.csv');
 assert.equal(get('compareStatus').focusCount,0);
 get('compareFile').files=[{name:'second.csv',size:1,text:async()=>{throw Error('unsafe fallback')}}];
 await get('compareFile').handlers.change();
 assert.equal(get('compareStatus').focusCount,1);
 assert.match(get('compareStatus').textContent,/Secure local file reader unavailable/);
 get('compareFile').files=[{name:'invalid.exe',size:1}];await get('compareFile').handlers.change();
 assert.equal(get('compareStatus').focusCount,2);
 get('compareFile').files=[{name:'too-large.csv',size:5000001}];await get('compareFile').handlers.change();
 assert.equal(get('compareStatus').focusCount,3);
 window.DataRescueFileReader={read:async()=>({rows:[['1']],normalizedHeaders:['id']})};
 get('compareFile').files=[{name:'valid.csv',size:1}];await get('compareFile').handlers.change();
 assert.equal(get('compareStatus').focusCount,3);
 assert.match(get('compareStatus').textContent,/Loaded second file: 1 rows/);
});
