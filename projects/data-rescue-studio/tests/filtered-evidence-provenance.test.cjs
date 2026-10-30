'use strict';
// Synthetic-only FT-01 source-record integrity regression.
// Filtered records without source positions must never be assigned fabricated IDs.
const assert = require('node:assert/strict');
const {exportEvidenceJson, exportIssueIndexJson, withoutExactDuplicates} = require('../rescue-core.js');
let checks = 0;
function ok(actual, expected, label) {
  assert.deepStrictEqual(actual, expected, label);
  checks++;
}
function rejects(action, label) {
  assert.throws(action, /source-record positions/, label);
  checks++;
}
function table(rows, extra = {}) {
  return {headers:['ID'], normalizedHeaders:['ID'], rows, warnings:[], delimiter:',', ...extra};
}
const filtered = table([['A'],['B']], {originalRowCount:5});
rejects(() => exportEvidenceJson(filtered), 'filtered evidence without original IDs');
rejects(() => exportIssueIndexJson(filtered), 'filtered issue index without original IDs');
rejects(() => withoutExactDuplicates(filtered), 'filtered deduplication without original IDs');
const mapped = table([['A'],['B']], {originalRowCount:5, sourceRecords:[2,6]});
ok(JSON.parse(exportEvidenceJson(mapped)).records.map(x => x.sourceRecord), [2,6],
  'exact evidence retains noncontiguous original IDs');
ok(withoutExactDuplicates(mapped).sourceRecords, [2,6],
  'deduplication retains noncontiguous original IDs');
const repeated = table([['A'],['A'],['B']], {originalRowCount:5, sourceRecords:[2,4,6]});
ok(withoutExactDuplicates(repeated).sourceRecords, [2,6],
  'deduplication preserves first original ID for repeated records');
const ordinary = table([['A'],['B']], {originalRowCount:2});
ok(JSON.parse(exportEvidenceJson(ordinary)).records.map(x => x.sourceRecord), [2,3],
  'ordinary sequential evidence remains supported');
ok(withoutExactDuplicates(ordinary).sourceRecords, [2,3],
  'ordinary sequential deduplication remains supported');
ok(JSON.parse(exportEvidenceJson(table([['A']]))).records[0].sourceRecord, 2,
  'legacy parsed input without original count remains supported');
ok(JSON.parse(exportIssueIndexJson(mapped)).recordCount, 2,
  'issue index still supports explicit original IDs');
const original = JSON.stringify(filtered);
rejects(() => exportEvidenceJson(filtered), 'repeat rejection is deterministic');
ok(JSON.stringify(filtered), original, 'failed exports do not mutate source input');
// The old implementation would have reported [2,3] for an original five-row
// source retaining rows [2,6]; the missing metadata cannot justify that claim.
assert.notDeepStrictEqual([2,3], [2,6], 'negative control distinguishes fabricated IDs');
checks++;
// Independently generated synthetic cases, no user data or external fixtures.
for (let i = 0; i < 1000; i++) {
  const originalRowCount = 3 + (i % 200);
  const count = 1 + (i % 2);
  const rows = Array.from({length:count}, (_, j) => ['K' + j]);
  const noPositions = table(rows, {originalRowCount});
  rejects(() => exportEvidenceJson(noPositions), 'filtered evidence scenario ' + i);
  rejects(() => withoutExactDuplicates(noPositions), 'filtered dedupe scenario ' + i);
  const sourceRecords = count === 1 ? [2] : [2, originalRowCount + 1];
  const valid = table(rows, {originalRowCount, sourceRecords});
  ok(JSON.parse(exportEvidenceJson(valid)).records.map(x => x.sourceRecord),
    sourceRecords, 'explicit provenance scenario ' + i);
}
console.log('FT-01 filtered evidence provenance: ' + checks + '/' + checks + ' PASS');
