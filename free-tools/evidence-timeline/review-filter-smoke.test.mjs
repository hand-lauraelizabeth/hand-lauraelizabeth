import assert from 'node:assert/strict';
import {filterReviewRows,reviewStatusSummary} from './review-filter.mjs';
const rows=[{sourceId:'000123',status:'reported'},{sourceId:'B',status:'disputed'}];
assert.deepEqual(filterReviewRows(rows,'reported').map(x=>x.sourceId),['000123']);
assert.equal(filterReviewRows(rows,'all').length,2);
assert.match(reviewStatusSummary(rows),/Disputed: 1/);
assert.equal(rows.length,2);
console.log('PASS: 4 synthetic filter assertions');
