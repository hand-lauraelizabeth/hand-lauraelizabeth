import assert from 'node:assert/strict';
import {evaluateWithProvenance, exportEvidenceCoverageCSV} from './evidence-coverage.mjs';

// Synthetic records only; output supports human review, not vendor selection.
const input={
  criteria:[{id:'C-0001',label:'Delivery plan',weight:100,mandatory:true,sourceRef:'REQ-0001'}],
  vendors:[{id:'供應商-0007',name:'Synthetic vendor',conflict:'none',price:'123.45'}],
  ratings:[{vendorId:'供應商-0007',criterionId:'C-0001',score:4,evidenceRef:'EV-0001',note:'Reviewed',reviewer:'QA'}]
};
const result=evaluateWithProvenance(input);
let count=0;
const check=(actual,expected)=>{assert.deepEqual(actual,expected);count++};
check(result.schema,'rfp-evaluation-v1');
check(result.vendors[0].id,'供應商-0007');
check(result.vendors[0].priceCents,12345);
check(result.criteria[0].sourceRef,'REQ-0001');
check(result.ratings[0].evidenceRef,'EV-0001');
check(result.comparisons[0].scorePercent,80);
const csv=exportEvidenceCoverageCSV(result);
check(csv.includes('"供應商-0007"'),true);
check(csv.includes('"REQ-0001"'),true);
check(csv.includes('"EV-0001"'),true);
check(csv.split('\r\n').filter(Boolean).length,2);
const missing=evaluateWithProvenance({...input,ratings:[{...input.ratings[0],evidenceRef:''}]});
check(missing.comparisons[0].scorePercent,null);
check(exportEvidenceCoverageCSV(missing).includes('Evidence reference missing'),true);
check(input.ratings[0].evidenceRef,'EV-0001');
const noReviewer=evaluateWithProvenance({...input,ratings:[{...input.ratings[0],reviewer:'\u200b\u0301'}]});
check(noReviewer.comparisons[0].reviewFlags.includes('Reviewer identifier missing: C-0001'),true);
check(noReviewer.comparisons[0].scorePercent,80);
check(exportEvidenceCoverageCSV(noReviewer).includes('Reviewer identifier missing'),true);
check(exportEvidenceCoverageCSV(result).includes('Reviewer identifier missing'),false);
console.log(`FT-07 provenance regression: ${count}/${count} assertions PASS`);
