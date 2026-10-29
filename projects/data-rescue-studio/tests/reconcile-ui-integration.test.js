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
const strictReader = require('../file-reader.js');
const engine = require('../reconcile-core.js');

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
  setAttribute(name, value) { this[name] = value; }
  removeAttribute(name) { delete this[name]; }
  remove() {}
}
const ids = ['compareFile','compareStatus','compareMetrics','compareResults',
  'compareRun','compareExport','compareJson','compareIndex','compareClear','leftKey','rightKey'];
const nodes = {};
for (const id of ids) {
  nodes[id] = new FakeElement(id === 'leftKey' || id === 'rightKey' ? 'select' : 'div');
  // The fixture must respect initial HTML disabled attributes, not merely JS defaults.
  nodes[id].disabled = ['leftKey','rightKey','compareRun','compareExport','compareJson','compareIndex'].includes(id);
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
const win = {DataRescue: rescue, DataReconcile: engine,
  DataRescueComparisonIndex: require('../comparison-issue-index.js'),
  // Existing synthetic async fixtures use text(); adapt them to a byte-backed
  // File before invoking the real strict reader. Real byte-backed fixtures
  // pass through unchanged for negative validation cases.
  DataRescueFileReader: {read: async (file, parser) => {
    if (typeof file.arrayBuffer === 'function') return strictReader.read(file, parser);
    const bytes = new TextEncoder().encode(await file.text());
    return strictReader.read({name:file.name,size:bytes.byteLength,
      arrayBuffer:async()=>bytes.buffer},parser);
  }}
};
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
  const safePreview=win.DataRescueCompareUI.previewText;
  check(typeof safePreview==='function','shared first-file/reconciliation preview helper exposed');
  const hidden='start\u200B'+'Z'.repeat(210)+'\nend';
  const visible=safePreview(hidden);
  check(visible.includes('\\u{200B}') && visible.includes('\\n'),'shared preview escapes hidden characters and line breaks');
  check(visible.includes('code points omitted') && !visible.includes('Z'.repeat(100)),'shared preview bounds long values');
  check(safePreview('short value')==='short value','short printable values unchanged');
  check(html.includes('DataRescueCompareUI.previewText(h)') && html.includes('DataRescueCompareUI.previewText(v)'),'first-file headers, quality metrics and cells use shared preview');
  const first=rescue.parseDelimited('ID,Value\n1,A\n2,B\n2,Duplicate\n3,C\n,Missing');
  win.DataRescueCompareUI.setPrimary(first,'first.csv');
  check(!nodes.leftKey.disabled,'first identifier select enabled');
  check(nodes.rightKey.disabled,'second identifier select disabled initially');
  check(nodes.compareRun.disabled,'compare disabled before second upload');
  check(nodes.leftKey.options.length===3,'first select has placeholder and both headings');
  const secondSource='Ref,Cost\n1,10\n2,20\n4,40\n,Missing';
  nodes.compareFile.files=[{name:'second.csv',size:secondSource.length,text:async()=>secondSource}];
  await nodes.compareFile.handlers.change();
  check(!nodes.rightKey.disabled,'second identifier select enabled');
  check(nodes.compareRun.disabled,'compare disabled until identifiers selected');
  nodes.leftKey.value='ID'; nodes.rightKey.value='Ref';
  nodes.leftKey.handlers.change();
  nodes.rightKey.handlers.change();
  check(!nodes.compareRun.disabled,'compare enabled when both keys chosen');
  nodes.compareRun.handlers.click();
  const counts=nodes.compareMetrics.children.map(node=>Number(node.children[1].textContent));
  assert.deepEqual(counts,[1,1,1,1,2,5,4,2,1]);count++;
  check(nodes.compareStatus.textContent.includes('Classified 5 of 5 first-file records and 4 of 4 second-file records'), 'completion status distinguishes source records from key groups');
  const originalReconcile=engine.reconcile;
  engine.reconcile=(...args)=>({...originalReconcile(...args),missingRight:[]});
  nodes.compareRun.handlers.click();
  check(nodes.compareExport.disabled && nodes.compareJson.disabled && nodes.compareIndex.disabled, 'incomplete reconciliation fails closed for every export');
  check(nodes.compareMetrics.children.length===0 && nodes.compareResults.children.length===0, 'incomplete reconciliation never displays misleading findings');
  check(nodes.compareStatus.role==='alert' && /Incomplete source-record coverage/.test(nodes.compareStatus.textContent), 'incomplete comparison produces actionable accessible error');
  engine.reconcile=originalReconcile;
  nodes.compareRun.handlers.click();
  check(!nodes.compareExport.disabled && !nodes.compareJson.disabled && !nodes.compareIndex.disabled, 'valid retry restores exports after coverage failure');
  check(nodes.compareResults.children.length===1,'visible result table created');
  check(!nodes.compareExport.disabled,'CSV audit enabled only after comparing');
  check(!nodes.compareJson.disabled,'JSON audit enabled only after comparing');
  check(!nodes.compareIndex.disabled,'privacy-minimized reconciliation index enabled after comparing');
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
  // A replacement primary must revoke an already loaded secondary source,
  // even when the new primary uses the same normalized identifier heading.
  win.DataRescueCompareUI.setPrimary(rescue.parseDelimited('ID,Value\n9,Replacement'),'replacement.csv');
  check(nodes.rightKey.disabled,'replacing primary clears loaded second-file key');
  check(nodes.compareFile.value==='','replacing primary clears second-file input');
  check(nodes.compareRun.disabled,'replacing primary disables stale comparison');
  check(nodes.compareExport.disabled && nodes.compareJson.disabled && nodes.compareIndex.disabled,'replacing primary revokes all old audits');
  nodes.compareClear.handlers.click();
  check(nodes.rightKey.disabled,'clear revokes second-file readiness');
  check(nodes.compareExport.disabled,'clear revokes stale CSV audit');
  check(nodes.compareJson.disabled,'clear revokes stale JSON audit');
  check(nodes.compareIndex.disabled,'clear revokes stale privacy index');
  // Replacing a file mid-read must ignore the older async completion.
  let finishRead;
  nodes.compareFile.files=[{name:'slow.csv',size:100,text:()=>new Promise(resolve=>finishRead=resolve)}];
  const pending=nodes.compareFile.handlers.change();
  nodes.compareClear.handlers.click();
  finishRead('Ref,Cost\n1,10');
  await pending;
  check(nodes.rightKey.disabled,'stale async file read ignored after clear');
  check(!nodes.compareStatus.textContent.includes('Loaded second file'),'stale file never shown as loaded');
  // A secondary read begun before primary replacement must never be adopted.
  let finishOldPrimaryRead;
  nodes.compareFile.files=[{name:'late.csv',size:100,text:()=>new Promise(resolve=>finishOldPrimaryRead=resolve)}];
  const oldPrimaryRead=nodes.compareFile.handlers.change();
  win.DataRescueCompareUI.setPrimary(rescue.parseDelimited('ID,Value\n8,Newer'),'new-primary.csv');
  finishOldPrimaryRead('Ref,Cost\n8,80');
  await oldPrimaryRead;
  check(nodes.rightKey.disabled && nodes.compareRun.disabled,'old secondary read ignored after primary replacement');
  check(!nodes.compareStatus.textContent.includes('Loaded second file'),'old secondary read cannot overwrite replacement status');
  nodes.compareFile.files=[{name:'payload.exe',size:10,text:async()=> 'x'}];
  await nodes.compareFile.handlers.change();
  check(nodes.compareStatus.className==='error','invalid extension produces error');
  check(nodes.compareRun.disabled,'invalid file cannot be compared');
  check(nodes.compareFile['aria-invalid']==='true' && nodes.compareStatus.role==='alert' && nodes.compareStatus['aria-live']==='assertive' && nodes.compareStatus.focused,
    'bad extension identifies secondary input and focuses assertive text error');
  nodes.compareFile.files=[{name:'oversized.csv',size:rescue.MAX_BYTES+1,text:async()=> {throw Error('should not read');}}];
  await nodes.compareFile.handlers.change();
  check(nodes.compareStatus.textContent.includes('larger than 5 MB'),'size rejected before read');
  check(nodes.compareFile['aria-invalid']==='true','oversized file retains invalid input state');
  // Fail closed when the shared strict byte reader is absent: never use text().
  const savedReader=win.DataRescueFileReader;
  win.DataRescueFileReader=null;
  nodes.compareFile.files=[{name:'fallback.csv',size:4,text:async()=> 'ID\\n1'}];
  await nodes.compareFile.handlers.change();
  check(nodes.compareStatus.className==='error' && nodes.compareStatus.textContent.includes('Strict local file reader is unavailable'),
    'missing strict reader fails closed rather than decoding text permissively');
  check(nodes.rightKey.disabled && nodes.compareRun.disabled,'missing reader leaves comparison disabled');
  check(nodes.compareFile['aria-invalid']==='true','unavailable strict reader marks upload invalid');
  win.DataRescueFileReader=savedReader;
  // The actual reader rejects malformed UTF-8, NUL, and byte-count mismatch.
  for (const [label, bytes, size, expected] of [
    ['malformed UTF-8',Uint8Array.from([73,68,10,0xC3]),4,'Invalid UTF-8'],
    ['embedded NUL',Uint8Array.from([73,68,10,0]),4,'NUL characters'],
    ['byte count mismatch',Uint8Array.from([73,68,10,49]),3,'byte count changed']
  ]) {
    nodes.compareFile.files=[{name:'invalid.csv',size,arrayBuffer:async()=>bytes.buffer}];
    await nodes.compareFile.handlers.change();
    check(nodes.compareStatus.className==='error' && nodes.compareStatus.textContent.includes(expected),
      label+' is rejected by strict byte reader');
    check(nodes.rightKey.disabled && nodes.compareRun.disabled,label+' cannot enable comparison');
    check(nodes.compareFile['aria-invalid']==='true' && nodes.compareStatus.role==='alert',label+' marks secondary input invalid and announces error');
  }
  win.DataRescueCompareUI.setPrimary(null);
  check(nodes.compareFile['aria-invalid']===undefined && nodes.compareStatus.role==='status', 'replacing primary clears stale secondary upload error');
  check(nodes.leftKey.disabled,'clearing first file disables comparison');
  const riskFirst=rescue.parseDelimited('ID\n=1+2');
  const riskSecond=rescue.parseDelimited('ID\n=1+2');
  win.DataRescueCompareUI.setPrimary(riskFirst,'one.csv');
  nodes.compareFile.files=[{name:'two.csv',size:8,text:async()=> 'ID\n=1+2'}];
  await nodes.compareFile.handlers.change();
  check(nodes.compareFile['aria-invalid']===undefined && nodes.compareStatus.role==='status' && nodes.compareStatus['aria-live']==='polite',
    'valid retry removes upload invalid state and restores polite status');
  nodes.leftKey.value='ID';nodes.rightKey.value='ID';
  nodes.leftKey.handlers.change();nodes.rightKey.handlers.change();
  nodes.compareRun.handlers.click();nodes.compareExport.handlers.click();
  const riskCsv=await blobs[1].text();
  check(riskCsv.includes('"\t=1+2"'),'spreadsheet-oriented export mitigates formula-like key');
  // A long, invisible-character identifier must be legible and bounded in the
  // preview without truncating the exact downloadable JSON audit.
  const longKey='A\u200B'+'B'.repeat(210)+'\n'+'tail';
  const quotedKey='"'+longKey+'"';
  win.DataRescueCompareUI.setPrimary(rescue.parseDelimited('ID\n'+quotedKey),'long-first.csv');
  nodes.compareFile.files=[{name:'long-second.csv',size:quotedKey.length+4,
    text:async()=> 'Ref\n'+quotedKey}];
  await nodes.compareFile.handlers.change();
  nodes.leftKey.value='ID'; nodes.rightKey.value='Ref';
  nodes.leftKey.handlers.change(); nodes.rightKey.handlers.change();
  nodes.compareRun.handlers.click();
  const previewKey=nodes.compareResults.children[0].children[2].children[0].children[1].textContent;
  check(previewKey.includes('\\u{200B}'),'invisible identifier character visible in preview');
  check(previewKey.includes('\\n'),'multiline identifier visibly escaped in preview');
  check(previewKey.includes('code points omitted'),'long preview states omission');
  check(!previewKey.includes('B'.repeat(100)),'preview bounds long identifier');
  const priorJsonCount=blobs.length;
  nodes.compareJson.handlers.click();
  const exactLongAudit=JSON.parse(await blobs[priorJsonCount].text());
  check(exactLongAudit.matches[0].key===longKey,'JSON preserves exact unbounded identifier');
  // Embedded newline followed by a formula marker must not create a CSV download.
  const multiline='safe\n=1+1';
  win.DataRescueCompareUI.setPrimary(rescue.parseDelimited('ID,Note\n"safe\n=1+1",private-field'),'unsafe-left.csv');
  nodes.compareFile.files=[{name:'unsafe-right.csv',size:25,text:async()=> 'Join\n"safe\n=1+1"'}];
  await nodes.compareFile.handlers.change();
  nodes.leftKey.value='ID';nodes.rightKey.value='Join';
  nodes.leftKey.handlers.change();nodes.rightKey.handlers.change();
  nodes.compareRun.handlers.click();
  const before=blobs.length;
  nodes.compareExport.handlers.click();
  check(blobs.length===before,'unsafe comparison CSV does not create blob');
  check(nodes.compareStatus.textContent.includes('audit record 2, column 2'),'CSV block identifies audit-output record');
  check(nodes.compareStatus.role==='alert' && nodes.compareStatus.focused,'CSV block is focused and announced');
  check(nodes.compareFile['aria-invalid']===undefined,'blocked CSV export does not mislabel the uploaded file');
  nodes.compareJson.handlers.click();
  check(blobs.length===before+1,'exact JSON comparison recovery creates blob');
  const json=JSON.parse(await blobs[before].text());
  check(json.format==='data-rescue-comparison-audit','JSON audit schema identified');
  check(json.matches[0].key===multiline && json.matches[0].leftRow===2 && json.matches[0].rightRow===2,
    'JSON audit preserves exact multiline key and source positions');
  check(!JSON.stringify(json).includes('private-field'),'JSON audit excludes non-key source cells');
  check(nodes.compareStatus.role==='status','JSON recovery restores normal status role');
  check(html.includes('<script src="reconcile-core.js"></script><script src="comparison-issue-index.js"></script><script src="reconcile-ui.js"></script>'),'scripts loaded before inline controller');
  check(html.includes('DataRescueCompareUI.setPrimary(data,name)'),'first-file load feeds reconciliation UI');
  check(html.includes('DataRescueCompareUI.setPrimary(null)'),'clearing first file invalidates comparison');
  check(/id="compareFile"[^>]*aria-describedby="compareStatus"/.test(html),'secondary upload is programmatically associated with error and status');
  check(html.includes('const ticket=loadEpoch') && html.includes('if(ticket!==loadEpoch)return'),'stale first file reads guarded');
  check(!/\bfetch\(|XMLHttpRequest|sendBeacon|\.submit\(/.test(html+ui),'browser interface does not upload data');
  console.log('PASS: '+count+' synthetic reconciliation UI integration assertions.');
}
run().catch(error=>{console.error(error);process.exitCode=1;});
