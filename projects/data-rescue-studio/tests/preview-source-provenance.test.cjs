'use strict';
// Synthetic-only regression for original logical record IDs in FT-01 previews.
const assert = require('node:assert/strict');
const core = require('../rescue-core.js');
let checks = 0;
function equal(actual, expected, label) {
  assert.deepStrictEqual(actual, expected, label); checks++;
}
function rejects(action, label) {
  assert.throws(action, /source-record/i, label); checks++;
}
function table(rows, extra = {}) {
  return {headers:['ID'], normalizedHeaders:['ID'], rows, warnings:[], delimiter:',', ...extra};
}
const mapped = table([['A'], ['A'], ['']], {sourceRecords:[2,4,6], originalRowCount:5});
equal(core.summarize(mapped).duplicateRows, [{row:4,firstSeen:2}], 'summary retains original duplicate IDs');
equal(core.inspectSourceRecords(mapped, 'all', 10).entries.map(e => e.sourceRecord),
  [2,4,6], 'preview retains original IDs');
equal(core.inspectSourceRecords(mapped, 'duplicates', 10).entries.map(e => e.duplicateOf),
  [2], 'preview duplicate points to original record');
equal(core.findSourceRecordOffset(mapped, 'all', 6), 2, 'find original record');
equal(core.findSourceRecordOffset(mapped, 'duplicates', 4), 0, 'find original duplicate');
equal(core.withoutExactDuplicates(mapped).sourceRecords, [2,6], 'dedupe preserves original IDs');
equal(core.summarize(table([['A'],['A']])).duplicateRows, [{row:3,firstSeen:2}],
  'ordinary sequential input remains supported');
equal(core.inspectSourceRecords(table([['A'],['B']]), 'all').entries.map(e => e.sourceRecord),
  [2,3], 'ordinary preview remains supported');
const invalid = [
  table([['A'],['B']], {originalRowCount:5}),
  table([['A'],['B']], {sourceRecords:[2,2], originalRowCount:5}),
  table([['A'],['B']], {sourceRecords:[4,2], originalRowCount:5}),
  table([['A'],['B']], {sourceRecords:[2], originalRowCount:5}),
  table([['A'],['B']], {sourceRecords:[2,7], originalRowCount:5}),
  table([['A'],['B']], {sourceRecords:null, originalRowCount:5}),
  table([['A'],['B']], {originalRowCount:1}),
  table([['A'],['B']], {originalRowCount:'5'})
];
for (const [i, input] of invalid.entries()) {
  rejects(() => core.summarize(input), 'invalid summary '+i);
  rejects(() => core.inspectSourceRecords(input), 'invalid preview '+i);
  rejects(() => core.findSourceRecordOffset(input, 'all', 2), 'invalid lookup '+i);
  rejects(() => core.withoutExactDuplicates(input), 'invalid dedupe '+i);
  rejects(() => core.spreadsheetExportRisk(input), 'invalid CSV warning '+i);
}
const risky = table([['=2+2']], {sourceRecords:[6], originalRowCount:5});
equal(core.spreadsheetExportRisk(risky), null,
  'known formula-like cell remains handled by existing CSV prefix mechanism');
const ambiguous = table([['\u2028']], {sourceRecords:[6], originalRowCount:5});
equal(core.spreadsheetExportRisk(ambiguous), {sourceRecord:6,column:1},
  'blocked spreadsheet export reports original source position');
for (let i=0;i<1000;i++) {
  const first=3+(i%300), second=first+2;
  const input=table([['same'],['same']], {sourceRecords:[first,second], originalRowCount:second-1});
  equal(core.summarize(input).duplicateRows, [{row:second,firstSeen:first}], 'summary '+i);
  equal(core.inspectSourceRecords(input, 'duplicates').entries.map(e=>e.sourceRecord),
    [second], 'preview '+i);
  equal(core.findSourceRecordOffset(input, 'duplicates', second), 0, 'lookup '+i);
  equal(core.withoutExactDuplicates(input).sourceRecords, [first], 'dedupe '+i);
}
console.log('FT-01 preview provenance: '+checks+'/'+checks+' PASS');
