import assert from 'node:assert/strict';
import {previewReplacement} from './replacement-preview.mjs';
const row = sourceId => ({sourceId, date:'2026-10-16', claim:'Synthetic'});
assert.throws(()=>previewReplacement([null],[]),/Invalid source ID/);
assert.throws(()=>previewReplacement([],[row(' ')]),/Invalid source ID/);
assert.throws(()=>previewReplacement([],[row('x'.repeat(121))]),/Invalid source ID/);
assert.equal(previewReplacement([row('café')],[row('cafe\u0301')]).added,1);
assert.equal(previewReplacement([row('000123')],[row('123')]).removed,1);
console.log('PASS: 5 malformed and exact-source regression checks');
