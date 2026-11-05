import assert from 'node:assert/strict';
import test from 'node:test';
import {chronology, exportCSV, exportJSON, validateWorkspace} from './core.mjs';

const request = {id:'REQ-00001',jurisdiction:'federal',agency:'Synthetic records office',stage:'submitted',submittedOn:'2026-10-20',agencyTrackingId:'0000123',description:'Synthetic test request'};
const event = i => ({id:`EVT-${String(i).padStart(5,'0')}`,requestId:request.id,date:'2026-10-21',kind:'note',sourceId:`SRC-${String(i).padStart(5,'0')}`,description:'Synthetic evidence'});
const build = count => ({version:1,requests:[{...request}],events:Array.from({length:count},(_,i)=>event(count-i))});

test('10,000 synthetic events: chronology and CSV retain exact source identifiers',()=>{
  const data=build(10000);
  const sorted=chronology(data);
  assert.equal(sorted.length,10000);
  assert.equal(sorted[0].id,'EVT-00001');
  assert.equal(sorted[0].sourceId,'SRC-00001');
  assert.equal(sorted.at(-1).id,'EVT-10000');
  assert.equal(sorted.at(-1).sourceId,'SRC-10000');
  const csv=exportCSV(data);
  const lines=csv.split('\r\n');
  assert.equal(lines.length,10003); // header + request + 10,000 events + terminal blank
  assert.ok(lines[2].includes('"SRC-00001"'));
  assert.ok(lines[10001].includes('"SRC-10000"'));
  const reopened=JSON.parse(exportJSON(data));
  assert.equal(reopened.events[0].sourceId,'SRC-10000'); // JSON preserves input order
  assert.equal(reopened.events.at(-1).sourceId,'SRC-00001');
  assert.equal(reopened.requests[0].agencyTrackingId,'0000123');
});

test('late malicious evidence blocks entire CSV while JSON remains exact',()=>{
  const data=build(10000);
  data.events[9999].sourceId='\u200f=HYPERLINK("https://example.invalid")';
  assert.throws(()=>exportCSV(data),/CSV export blocked/);
  assert.equal(JSON.parse(exportJSON(data)).events[9999].sourceId,data.events[9999].sourceId);
});

test('record limits and duplicate identifiers fail closed',()=>{
  assert.throws(()=>validateWorkspace(build(10001)),/record limit exceeded/);
  const tooManyRequests=build(0);
  tooManyRequests.requests=Array.from({length:1001},(_,i)=>({...request,id:`REQ-${i}`}));
  assert.throws(()=>exportCSV(tooManyRequests),/record limit exceeded/);
  const duplicated=build(2);
  duplicated.events[1].id=duplicated.events[0].id;
  assert.throws(()=>exportCSV(duplicated),/Duplicate event ID/);
});
