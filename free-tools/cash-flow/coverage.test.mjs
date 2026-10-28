import test from 'node:test';
import assert from 'node:assert/strict';
import {summarizeEventCoverage,coverageText} from './coverage.mjs';
const events=(...ids)=>ids.map(id=>({id}));
const projection=(...ids)=>({days:[{events:ids.map(id=>({id}))}]});
test('empty schedule is described without implying payments',()=>{
  assert.match(coverageText([],projection(),projection()),/only the opening balance/);
});
test('every event present in both projections',()=>{
  assert.deepEqual(summarizeEventCoverage(events('rent'),projection('rent'),projection('rent')),{baselineMissing:[],scenarioMissing:[]});
  assert.match(coverageText(events('rent'),projection('rent'),projection('rent')),/All 1 event has/);
});
test('one-off outside both projection windows remains identified',()=>{
  const text=coverageText(events('rent','future-bill'),projection('rent'),projection('rent'));
  assert.match(text,/baseline 1 of 2 \["future-bill"\]/);
  assert.match(text,/shifted scenario 1 of 2 \["future-bill"\]/);
  assert.match(text,/remain in your editable plan/);
});
test('baseline-only occurrence is absent from scenario',()=>{
  assert.deepEqual(summarizeEventCoverage(events('rent'),projection('rent'),projection()),{baselineMissing:[],scenarioMissing:['rent']});
});
test('scenario-only occurrence is absent from baseline',()=>{
  assert.deepEqual(summarizeEventCoverage(events('rent'),projection(),projection('rent')),{baselineMissing:['rent'],scenarioMissing:[]});
});
test('repeated occurrences count once and preserve padded source IDs',()=>{
  const id=' 00009 ';
  assert.deepEqual(summarizeEventCoverage(events(id),projection(id,id),projection(id)),{baselineMissing:[],scenarioMissing:[]});
});
test('display escapes invisible direction controls without altering source IDs',()=>{
  const id='invoice\u202E01';
  assert.deepEqual(summarizeEventCoverage(events(id),projection(),projection()).baselineMissing,[id]);
  const text=coverageText(events(id),projection(),projection());
  assert.match(text,/invoice\\u202E01/);
  assert.ok(!text.includes('\u202E'));
});
test('preview is bounded but total counts remain exact',()=>{
  const ids=['a','b','c','d','e','f'];
  const text=coverageText(events(...ids),projection(),projection());
  assert.match(text,/baseline 6 of 6/);
  assert.match(text,/2 more/);
  assert.ok(!text.includes('"f"'));
});
test('invalid projections cannot silently imply full coverage',()=>{
  assert.throws(()=>summarizeEventCoverage(events('a'),{days:[{}]},projection()),/Invalid projection event list/);
  assert.throws(()=>summarizeEventCoverage(events('a'),{},projection()),/Invalid event coverage inputs/);
});

test('rejects duplicate source IDs instead of counting ambiguous events as covered',()=>{
  assert.throws(()=>summarizeEventCoverage(events('rent','rent'),projection('rent'),projection('rent')),/Duplicate source event ID/);
});
test('rejects an unrecognized baseline event ID rather than silently accepting a corrupted projection',()=>{
  assert.throws(()=>coverageText(events('rent'),projection('rent','ghost'),projection('rent')),/Projection event ID does not match/);
});
test('rejects an unrecognized shifted-scenario ID independently of baseline coverage',()=>{
  assert.throws(()=>summarizeEventCoverage(events('rent'),projection('rent'),projection('rent','other')),/Projection event ID does not match/);
});
test('rejects missing and nonstring projection event identities',()=>{
  assert.throws(()=>coverageText(events('rent'),{days:[{events:[{}]}]},projection('rent')),/Projection event ID does not match/);
  assert.throws(()=>coverageText(events('rent'),projection('rent'),{days:[{events:[{id:42}]}]}),/Projection event ID does not match/);
});
test('source identity matching preserves exact whitespace and unusual but valid IDs',()=>{
  const id=' 00\u202E9 ';
  assert.deepEqual(summarizeEventCoverage(events(id),projection(id),projection(id)),{baselineMissing:[],scenarioMissing:[]});
});
