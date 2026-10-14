import assert from 'node:assert/strict';
import {buildEvidenceMatrix} from './review-matrix.mjs';
assert.deepEqual(buildEvidenceMatrix([]),[]);
console.log('Empty matrix PASS');
