import assert from 'node:assert/strict';
import {evaluateMatrix,exportEvidenceCoverageCSV} from './core.mjs';

// Synthetic procurement records only. Missing source evidence cannot yield a finalized score.
const fixture={
 criteria:[{id:'req-001',label:'Security controls',weight:100,mandatory:true,sourceRef:''}],
 vendors:[{id:'vendor-0007',name:'Example vendor',conflict:'unreviewed',price:'1200.05'}],
 ratings:[{vendorId:'vendor-0007',criterionId:'req-001',score:4,evidenceRef:'file-009',note:'Synthetic evidence',reviewer:'QA'}]
};
const result=evaluateMatrix(fixture);
assert.equal(result.comparisons.length,1);
assert.equal(result.comparisons[0].scorePercent,null,'missing criterion source must withhold score');
assert.ok(result.comparisons[0].reviewFlags.some(x=>x.includes('Criterion source missing')));
assert.equal(result.comparisons[0].priceCents,120005);
const csv=exportEvidenceCoverageCSV(result);
assert.match(csv,/vendorConflictStatus/);
assert.match(csv,/vendorPriceCents/);
assert.match(csv,/vendorReviewIssues/);
assert.match(csv,/criterionSourceRef/);
assert.match(csv,/vendor-0007/);
assert.match(csv,/120005/);
assert.match(csv,/Criterion source missing/);
assert.match(csv,/Conflict review required/);
assert.equal(csv.trimEnd().split('\r\n').length,2);
console.log('PASS: 12 synthetic FT-07 provenance and vendor-context assertions');
