'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const base = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(base, 'reconcile-ui.js'), 'utf8');
const reader = require('../file-reader.js');
const core = require('../rescue-core.js');
const reconcile = require('../reconcile-core.js');
const makeFile = (name, text) => {
  const bytes = new TextEncoder().encode(text);
  return {name, size:bytes.byteLength, arrayBuffer:async()=>bytes.slice().buffer};
};
function harness() {
  const nodes = new Map();
  function get(id) {
    if (!nodes.has(id)) nodes.set(id, {
      id, value:'', files:[], options:[], disabled:false, textContent:'', className:'',
      children:[], focusCount:0, handlers:{},
      focus(){this.focusCount++},
      addEventListener(event, fn){this.handlers[event]=fn},
      replaceChildren(...items){this.children=items;this.options=items;this.value=''},
      append(...items){this.children.push(...items);this.options=this.children},
      click(){}, remove(){}
    });
    return nodes.get(id);
  }
  const document = {getElementById:get,createElement:()=>({
    value:'',textContent:'',children:[],append(...items){this.children.push(...items)},
    replaceChildren(){},click(){},remove(){}
  }),body:{append(){}}};
  const window = {DataRescue:core, DataReconcile:reconcile, DataRescueFileReader:reader};
  vm.runInNewContext(source,{window,document,Blob,URL:{createObjectURL(){return 'blob:test'},revokeObjectURL(){}},setTimeout(){}});
  window.DataRescueCompareUI.setPrimary(core.parseDelimited('ID,Name\n1,Alpha'),'primary.csv');
  return {get,window};
}
test('secondary import uses real strict byte reader and keeps source local', async()=>{
  const {get}=harness();
  get('compareFile').files=[makeFile('secondary.csv','ID,Name\n1,Élodie')];
  await get('compareFile').handlers.change();
  assert.match(get('compareStatus').textContent,/Loaded second file: 1 rows/);
  assert.equal(get('compareStatus').focusCount,0);
  assert.equal(get('rightKey').disabled,false);
});
test('invalid UTF-8 and embedded NUL fail closed with focus',async()=>{
  const {get}=harness();
  get('compareFile').files=[{name:'bad.csv',size:2,arrayBuffer:async()=>Uint8Array.from([0xc3,0x28]).buffer}];
  await get('compareFile').handlers.change();
  assert.match(get('compareStatus').textContent,/Invalid UTF-8/);
  assert.equal(get('compareStatus').focusCount,1);
  assert.equal(get('rightKey').disabled,true);
  get('compareFile').files=[makeFile('nul.csv','ID\u0000,Name\n1,Alpha')];
  await get('compareFile').handlers.change();
  assert.match(get('compareStatus').textContent,/NUL characters/);
  assert.equal(get('compareStatus').focusCount,2);
});
test('stale read cannot resurrect a cleared second file',async()=>{
  const {get}=harness();
  let finish;
  get('compareFile').files=[{name:'late.csv',size:16,arrayBuffer:()=>new Promise(resolve=>{finish=resolve})}];
  const pending=get('compareFile').handlers.change();
  get('compareClear').handlers.click();
  finish(new TextEncoder().encode('ID\n1').buffer);
  await pending;
  assert.equal(get('rightKey').disabled,true);
  assert.doesNotMatch(get('compareStatus').textContent,/Loaded second file/);
});
