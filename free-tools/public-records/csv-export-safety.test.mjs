import test from 'node:test';
import assert from 'node:assert/strict';
import {exportCSV, exportJSON, validateWorkspace} from './core.mjs';
import {bindExports} from './export-ui.mjs';

const fixture = () => ({version:1,
  requests:[{id:'REQ-0007',jurisdiction:'federal',agency:'Fictional Records Office',stage:'submitted',submittedOn:'2026-10-20',agencyTrackingId:'TRACK-007',description:'Records, part "A"\ncontinued'}],
  events:[{id:'EV-0001',requestId:'REQ-0007',date:'2026-10-21',kind:'note',sourceId:'SRC-0009',description:'Synthetic note'}]});

test('untrusted CSV fields fail closed; JSON retains exact source strings', () => {
  const risky=['=2+2','+SUM(A1:A2)','-1+2','@SUM(A1)','＝SUM(A1)','\u202Eabc','abc\u2066def','\u200B\u0301=1+1','\uFE0F+1','abc,=HYPERLINK(1)','abc;@SUM(A1)','abc\t=1','abc\n=1','\u0001abc','\u061Cleft','\u2028new'];
  for (const field of ['agency','agencyTrackingId','description','sourceId']) for (const value of risky) {
    const w=fixture(); const record=field==='sourceId'?w.events[0]:w.requests[0];record[field]=value;
    assert.equal(JSON.parse(exportJSON(w))[field==='sourceId'?'events':'requests'][0][field],value);
    assert.throws(()=>exportCSV(w),/CSV export blocked/);
  }
});

test('safe multilingual, quoted and multiline records export with exact provenance', () => {
  const w=fixture();w.requests[0].agency='مكتب سجلات ٢٠٢٦';w.events[0].description='"quoted", second line\ncontinued';
  const csv=exportCSV(w);
  assert.ok(csv.includes('"REQ-0007"'));
  assert.ok(csv.includes('"SRC-0009"'));
  assert.ok(csv.includes('"مكتب سجلات ٢٠٢٦"'));
  assert.ok(csv.includes('"""quoted"", second line\ncontinued"'));
  assert.ok(csv.endsWith('\r\n'));
  assert.equal(validateWorkspace(JSON.parse(exportJSON(w))).events[0].sourceId,'SRC-0009');
});

test('unsafe CSV button cannot download, but lossless JSON remains available', () => {
  const handlers=new Map();const messages=[];let downloads=0;
  const oldDocument=globalThis.document, oldURL=globalThis.URL;
  globalThis.document={getElementById:id=>({addEventListener:(_,fn)=>handlers.set(id,fn)}),createElement:()=>({click:()=>{downloads++},remove(){}}),body:{append(){}}};
  globalThis.URL={createObjectURL:()=> 'blob:synthetic',revokeObjectURL:()=>{}};
  try {
    const w=fixture();w.requests[0].agency='\u202Euntrusted';
    bindExports(()=>w,message=>messages.push(message));
    handlers.get('save-csv')();assert.equal(downloads,0);
    assert.match(messages.at(-1),/CSV unavailable: CSV export blocked/);
    assert.match(messages.at(-1),/data is unchanged/);
    handlers.get('save-json')();assert.equal(downloads,1);
    assert.equal(w.requests[0].agency,'\u202Euntrusted');
  } finally {globalThis.document=oldDocument;globalThis.URL=oldURL;}
});