import assert from 'node:assert/strict';
import {normalizeEvidence,exportEvidenceCSV} from './core.mjs';
const row={sourceId:' A ',date:'2024-02-29',claim:' claim ',group:' group '};
const [result]=normalizeEvidence([row]);
assert.equal(result.sourceId,' A ');
assert.equal(result.claim,' claim ');
assert.equal(result.group,' group ');
assert.throws(()=>normalizeEvidence([{...row,sourceId:' A '},{...row}]),/duplicate/i);
assert.throws(()=>normalizeEvidence([{...row,group:'x'.repeat(121)}]),/classification/i);
assert.throws(()=>normalizeEvidence([{...row,claim:' '.repeat(4)}]),/claim/i);
for(const prefix of ['＝','＋','－','＠']){
  const csv=exportEvidenceCSV([{...row,claim:prefix+'SUM(1,2)'}]);
  assert.ok(csv.includes('"\u0027'+prefix+'SUM(1,2)"'));
}
console.log('PASS: 10 legacy exact-source and fullwidth CSV checks');
