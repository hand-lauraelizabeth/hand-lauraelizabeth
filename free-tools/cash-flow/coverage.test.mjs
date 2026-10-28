import test from 'node:test';
import assert from 'node:assert/strict';
import {summarizeEventCoverage,coverageText,displaySafeText} from './coverage.mjs';
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

test('long source IDs have bounded, explicitly shortened status previews without changing exact identities',()=>{
  const id='a'.repeat(60)+'b'.repeat(5000)+'z'.repeat(12);
  const text=coverageText(events(id),projection(),projection());
  assert.match(text,/5000 code points omitted from displayed ID/);
  assert.ok(text.includes('a'.repeat(60)));
  assert.ok(text.includes('z'.repeat(12)));
  assert.ok(!text.includes('b'.repeat(5000)));
  assert.ok(text.length<1500);
  assert.deepEqual(summarizeEventCoverage(events(id),projection(),projection()).baselineMissing,[id]);
});
test('preview shortening counts Unicode code points rather than UTF-16 units',()=>{
  const id='🧾'.repeat(100);
  const text=coverageText(events(id),projection(),projection());
  assert.match(text,/28 code points omitted from displayed ID/);
  assert.deepEqual(summarizeEventCoverage(events(id),projection(),projection()).scenarioMissing,[id]);
});
test('status escapes additional invisible format characters but preserves exact IDs',()=>{
  const id='ID\u00ad\u034f\ufeff\u2060\u{e0001}';
  const text=coverageText(events(id),projection(),projection());
  for(const ch of ['\u00ad','\u034f','\ufeff','\u2060','\u{e0001}'])assert.ok(!text.includes(ch));
  for(const escape of ['\\u00AD','\\u034F','\\uFEFF','\\u2060','\\uE0001'])assert.ok(text.includes(escape));
  assert.deepEqual(summarizeEventCoverage(events(id),projection(),projection()).baselineMissing,[id]);
});
test('four very long missing IDs cannot create an unbounded status message',()=>{
  const ids=Array.from({length:6},(_,i)=>String(i)+'x'.repeat(10000));
  const text=coverageText(events(...ids),projection(),projection());
  assert.match(text,/baseline 6 of 6/);
  assert.match(text,/2 more/);
  assert.ok(text.length<4500);
});

test('full Unicode default-ignorable class is visibly escaped in status, with exact matching unchanged',()=>{
  const id='bill\u3164\uffa0\u2065\u{e0061}';
  const text=coverageText(events(id),projection(),projection());
  for(const ch of ['\u3164','\uffa0','\u2065','\u{e0061}'])assert.ok(!text.includes(ch));
  for(const escaped of ['\\u3164','\\uFFA0','\\u2065','\\uE0061'])assert.ok(text.includes(escaped));
  assert.deepEqual(summarizeEventCoverage(events(id),projection(),projection()).baselineMissing,[id]);
});
test('Unicode line separators and DEL are escaped without introducing new status lines',()=>{
  const id='bill\u2028due\u2029today\u007f';
  const text=coverageText(events(id),projection(),projection());
  for(const ch of ['\u2028','\u2029','\u007f'])assert.ok(!text.includes(ch));
  for(const escaped of ['\\u2028','\\u2029','\\u007F'])assert.ok(text.includes(escaped));
  assert.equal(text.split('\n').length,1);
});
test('ordinary Unicode letters and visible emoji remain readable',()=>{
  const id='café-🧾-請求書';
  const text=coverageText(events(id),projection(),projection());
  assert.ok(text.includes(id));
  assert.deepEqual(summarizeEventCoverage(events(id),projection(id),projection(id)).baselineMissing,[]);
});

test('event-list display exposes hidden directional and zero-width controls without mutating IDs',()=>{
  const id='rent\u202E\u200B-01';
  const shown=displaySafeText(id);
  assert.match(shown,/rent\\\\u202E\\\\u200B-01/);
  assert.ok(!shown.includes('\u202E'));
  assert.ok(!shown.includes('\u200B'));
  assert.deepEqual(summarizeEventCoverage(events(id),projection(id),projection(id)).baselineMissing,[]);
});
test('event descriptions with embedded quotes and line breaks display as one readable string',()=>{
  const label='Invoice "paid"\nnext line\u2029end';
  const shown=displaySafeText(label);
  assert.ok(shown.includes('Invoice \\"paid\\"'));
  assert.ok(shown.includes('\\\\n'));
  assert.ok(shown.includes('\\\\u2029'));
  assert.equal(shown.split('\n').length,1);
});
test('long event descriptions use bounded display-only previews',()=>{
  const label='start'.repeat(12)+'X'.repeat(600)+'ending'.repeat(2);
  const shown=displaySafeText(label);
  assert.match(shown,/600 code points omitted from displayed ID/);
  assert.ok(shown.length<180);
  assert.ok(!shown.includes('X'.repeat(600)));
});
