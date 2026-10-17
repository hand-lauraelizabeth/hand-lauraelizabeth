import assert from 'node:assert/strict';
import {previewReplacement} from './replacement-preview.mjs';
const rec = sourceId => ({sourceId, date:'2026-10-16', claim:'Synthetic'});
assert.throws(() => previewReplacement([rec('x'),rec('x')], []), /Duplicate/);
assert.throws(() => previewReplacement([], [rec('x'),rec('x')]), /Duplicate/);
assert.equal(previewReplacement([rec(' A ')],[rec('A')]).added,1);
console.log('PASS: duplicate and exact-ID guard checks');
