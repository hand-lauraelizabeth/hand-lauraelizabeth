import assert from 'node:assert/strict';
import test from 'node:test';
import { validateWorkspace, reviewFlags, chronology, exportCSV, exportJSON } from './core.mjs';

// All records are synthetic. No network access or personal records are required.
const request = (id, stage='draft') => ({
  id, jurisdiction:'federal', agency:'Example agency', stage,
  submittedOn:'', agencyTrackingId:'', description:'Synthetic request'
});
const event = (id, requestId, date='2026-10-21') => ({
  id, requestId, date, kind:'note', sourceId:'synthetic-source',
  description:'Synthetic event'
});
const workspace = (requests, events=[]) => ({version:1,requests,events});

test('missing evidence is explicit, and a documented response clears only its own flag', () => {
  const submitted=request('r-submitted','submitted');
  const responded=request('r-responded','responded');
  const w=workspace([request('r-draft'),submitted,responded]);
  assert.deepEqual(reviewFlags(w),[
    {requestId:'r-submitted',flags:['Submission date not recorded','Agency tracking ID not recorded']},
    {requestId:'r-responded',flags:['Submission date not recorded','Agency tracking ID not recorded','Response event not recorded']}
  ]);
  const response={...event('e-response','r-responded'),kind:'response'};
  assert.deepEqual(reviewFlags(workspace(w.requests,[response]))[1].flags,[
    'Submission date not recorded','Agency tracking ID not recorded'
  ]);
});

test('chronology orders equal dates by event ID without changing exact source IDs', () => {
  const w=workspace([request('r1')],[
    {...event('e-z','r1','2026-10-21'),sourceId:'Source:0003'},
    {...event('e-a','r1','2026-10-21'),sourceId:'Source:0001'},
    {...event('e-b','r1','2026-10-20'),sourceId:'Source:0002'}
  ]);
  assert.deepEqual(chronology(w).map(e=>e.id),['e-b','e-a','e-z']);
  assert.deepEqual(JSON.parse(exportJSON(w)).events.map(e=>e.sourceId),
    ['Source:0003','Source:0001','Source:0002']);
});

test('unsafe spreadsheet content fails closed while JSON preserves exact text', () => {
  for (const payload of ['=1+1','＋SUM(1,1)','\u202eABC','prefix,=HYPERLINK("x")','\t@SUM(1)']) {
    const r={...request('r1'),description:payload};
    const w=workspace([r]);
    assert.throws(()=>exportCSV(w),/CSV export blocked/);
    assert.equal(JSON.parse(exportJSON(w)).requests[0].description,payload);
  }
  const safe=workspace([{...request('r1'),description:'Comma, quote " and Unicode café'}]);
  assert.match(exportCSV(safe),/"Comma, quote "" and Unicode café"/);
});

test('workspace limits and cross-record references are enforced before export', () => {
  const maxRequests=Array.from({length:1000},(_,i)=>request('r'+i));
  const maxEvents=Array.from({length:10000},(_,i)=>event('e'+i,'r0'));
  assert.equal(validateWorkspace(workspace(maxRequests,maxEvents)).events.length,10000);
  assert.throws(()=>validateWorkspace(workspace([...maxRequests,request('overflow')])),/limit exceeded/);
  assert.throws(()=>validateWorkspace(workspace([request('r0')],[...maxEvents,event('overflow','r0')])),/limit exceeded/);
  assert.throws(()=>validateWorkspace(workspace([request('r0'),request('r0')])),/Duplicate request ID/);
  assert.throws(()=>validateWorkspace(workspace([request('r0')],[event('e0','unknown')])),/unknown request/);
});
