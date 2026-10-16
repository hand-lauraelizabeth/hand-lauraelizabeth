/* Synthetic browser-controller integration checks; no DOM or network packages required. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const ui = fs.readFileSync(path.join(root, 'reconcile-ui.js'), 'utf8');
const rescue = require('../rescue-core.js');
const engine = require('../reconcile-core.js');
const reader = require('../file-reader.js');
const bytes = text => new TextEncoder().encode(text).buffer;

class FakeElement {
  constructor(tag='div') {
    this.tagName = tag;
    this.children = [];
    this.options = [];
    this.handlers = {};
    this.disabled = false;
    this.value = '';
    this.files = [];
    this.textContent = '';
  }
  addEventListener(type, callback) { this.handlers[type] = callback; }
  append(...children) {
    this.children.push(...children);
    if (this.tagName === 'select') this.options = this.children;
  }
  replaceChildren(...children) {
    this.children = children;
    if (this.tagName === 'select') {
      this.options = children;
      this.value = '';
    }
  }
  click() { this.clicked = true; }
  focus() { this.focused = true; }
  remove() {}
}
const ids = ['compareFile','compareStatus','compareMetrics','compareResults',
  'compareRun','compareExport','compareClear','leftKey','rightKey'];
const nodes = {};
for (const id of ids) {
  nodes[id] = new FakeElement(id === 'leftKey' || id === 'rightKey' ? 'select' : 'div');
  // The fixture must respect initial HTML disabled attributes, not merely JS defaults.
  nodes[id].disabled = ['leftKey','rightKey','compareRun','compareExport'].includes(id);
}
const document = {
  body: new FakeElement('body'),
  getElementById: id => {
    assert.ok(nodes[id], 'known element: ' + id);
    return nodes[id];
  },
  createElement: tag => new FakeElement(tag)
};
const blobs = [], downloads = [];
const win = {DataRescue: rescue, DataReconcile: engine, DataRescueFileReader: reader};
const ctx = {window:win, document,
  Blob,
  URL: {createObjectURL(blob){blobs.push(blob);return 'blob:synthetic-' + blobs.length;},
        revokeObjectURL(url){downloads.push(url);}},
  setTimeout(callback){callback();}
};
vm.runInNewContext(ui, ctx, {filename:'reconcile-ui.js'});
let count=0;
function check(value,label) { assert.ok(value,label); count++; }
async function run() {
  check(typeof win.DataRescueCompareUI.setPrimary === 'function','UI controller exposed locally');
  const first=rescue.parseDelimited('ID,Value\n1,A\n2,B\n2,Duplicate\n3,C\n,Missing');
  win.DataRescueCompareUI.setPrimary(first,'first.csv');
  check(!nodes.leftKey.disabled,'first identifier select enabled');
  check(nodes.rightKey.disabled,'second identifier select disabled initially');
  check(nodes.compareRun.disabled,'compare disabled before second upload');
  check(nodes.leftKey.options.length===3,'first select has placeholder and both headings');
  const secondSource='Ref,Cost\n1,10\n2,20\n4,40\n,Missing';
  nodes.compareFile.files=[{name:'second.csv',size:secondSource.length,arrayBuffer:async()=>bytes(secondSource)}];
  await nodes.compareFile.handlers.change();
  check(!nodes.rightKey.disabled,'second identifier select enabled');
  check(nodes.compareRun.disabled,'compare disabled until identifiers selected');
  nodes.leftKey.value='ID'; nodes.rightKey.value='Ref';
  nodes.leftKey.handlers.change();
  nodes.rightKey.handlers.change();
  check(!nodes.compareRun.disabled,'compare enabled when both keys chosen');
  nodes.compareRun.handlers.click();
  const counts=nodes.compareMetrics.children.map(node=>Number(node.children[1].textContent));
  assert.deepEqual(counts,[1,1,1,1,2]);count++;
  check(nodes.compareResults.children.length===1,'visible result table created');
  check(!nodes.compareExport.disabled,'audit enabled only after comparing');
  check(nodes.compareStatus.textContent.includes('ambiguous identifier groups'),'ambiguity reported in status');
  nodes.compareExport.handlers.click();
  check(blobs.length===1,'export creates one local blob');
  const csv=await blobs[0].text();
  const audit=rescue.parseDelimited(csv);
  check(audit.rows.length===6,'all six findings exported, not preview-only');
  check(audit.rows.some(row=>row[0].startsWith('Ambiguous') && row[2]==='3; 4'),'duplicate row references retained');
  check(audit.rows.some(row=>row[0]==='Missing second-file key' && row[3]==='5'),'missing key trace retained');
  check(!csv.includes('Duplicate'),'source data fields omitted from audit');
  check(downloads.length===1,'blob URL revoked after download');
  nodes.compareClear.handlers.click();
  check(nodes.rightKey.disabled,'clear revokes second-file readiness');
  check(nodes.compareExport.disabled,'clear revokes stale audit');
  // Replacing a file mid-read must ignore the older async completion.
  let finishRead;
  nodes.compareFile.files=[{name:'slow.csv',size:100,arrayBuffer:()=>new Promise(resolve=>finishRead=resolve)}];
  const pending=nodes.compareFile.handlers.change();
  nodes.compareClear.handlers.click();
  finishRead(bytes('Ref,Cost\n1,10'));
  await pending;
  check(nodes.rightKey.disabled,'stale async file read ignored after clear');
  check(!nodes.compareStatus.textContent.includes('Loaded second file'),'stale file never shown as loaded');
  nodes.compareFile.files=[{name:'payload.exe',size:10,arrayBuffer:async()=>bytes('x')}];
  await nodes.compareFile.handlers.change();
  check(nodes.compareStatus.className==='error','invalid extension produces error');
  check(nodes.compareRun.disabled,'invalid file cannot be compared');
  check(nodes.compareStatus.focused === true,'invalid file error receives keyboard focus');
  nodes.compareFile.files=[{name:'oversized.csv',size:rescue.MAX_BYTES+1,arrayBuffer:async()=> {throw Error('should not read');}}];
  await nodes.compareFile.handlers.change();
  check(nodes.compareStatus.textContent.includes('larger than 5 MB'),'size rejected before read');
  win.DataRescueCompareUI.setPrimary(null);
  check(nodes.leftKey.disabled,'clearing first file disables comparison');
  const riskFirst=rescue.parseDelimited('ID\n=1+2');
  const riskSecond=rescue.parseDelimited('ID\n=1+2');
  win.DataRescueCompareUI.setPrimary(riskFirst,'one.csv');
  nodes.compareFile.files=[{name:'two.csv',size:8,arrayBuffer:async()=>bytes('ID\n=1+2')}];
  await nodes.compareFile.handlers.change();
  nodes.leftKey.value='ID';nodes.rightKey.value='ID';
  nodes.leftKey.handlers.change();nodes.rightKey.handlers.change();
  nodes.compareRun.handlers.click();nodes.compareExport.handlers.click();
  const riskCsv=await blobs[1].text();
  check(riskCsv.includes('"\t=1+2"'),'spreadsheet-oriented export mitigates formula-like key');
  check(html.includes('<script src="reconcile-core.js"></script><script src="reconcile-ui.js"></script>'),'scripts loaded before inline controller');
  check(html.includes('DataRescueCompareUI.setPrimary(data,name)'),'first-file load feeds reconciliation UI');
  check(html.includes('DataRescueCompareUI.setPrimary(null)'),'clearing first file invalidates comparison');
  check(html.includes('const ticket=loadEpoch') && html.includes('if(ticket!==loadEpoch)return'),'stale first file reads guarded');
  check(!/\bfetch\(|XMLHttpRequest|sendBeacon|\.submit\(/.test(html+ui),'browser interface does not upload data');
  console.log('PASS: '+count+' synthetic reconciliation UI integration assertions.');
}
run().catch(error=>{console.error(error);process.exitCode=1;});
