import assert from 'node:assert/strict';
import {evaluateWithProvenance,exportEvidenceCoverageCSV} from './evidence-coverage.mjs';
let checks=0;const eq=(a,b)=>{assert.deepEqual(a,b);checks++};const yes=x=>{assert.ok(x);checks++};
const input={
 criteria:[{id:'criterion-001',label:'Privacy',weight:60,mandatory:true,sourceRef:''},{id:'criterion-002',label:'Support',weight:40,mandatory:false,sourceRef:'RFP §2'}],
 vendors:[{id:'vendor-0001',name:'Synthetic supplier',conflict:'unreviewed',price:'1234.05'},{id:'vendor-0002',name:'Other supplier',conflict:'none',price:''}],
 ratings:[{vendorId:'vendor-0001',criterionId:'criterion-001',score:4,evidenceRef:'doc-0001',note:'Reviewed',reviewer:'QA'},{vendorId:'vendor-0001',criterionId:'criterion-002',score:5,evidenceRef:'doc-0002',note:'',reviewer:'QA'}]
};
const result=evaluateWithProvenance(input);
eq(result.comparisons[0].scorePercent,null);
eq(result.comparisons[1].scorePercent,null);
yes(result.comparisons[0].reviewFlags.some(f=>f.includes('Criterion source missing')));
eq(result.vendors[0].priceCents,123405);
const csv=exportEvidenceCoverageCSV(result);
for(const header of ['vendorConflictStatus','vendorPriceCents','vendorReviewIssues','criterionSourceRef','mandatory','reviewIssues'])yes(csv.includes(header));
yes(csv.includes('"vendor-0001"'));
yes(csv.includes('"123405"'));
yes(csv.includes('Criterion source missing'));
yes(csv.includes('Conflict review required'));
yes(csv.includes('Price not supplied'));
yes(csv.includes('Rating record missing'));
eq(csv.trimEnd().split('\r\n').length,5);
assert.throws(()=>evaluateWithProvenance({...input,criteria:[{...input.criteria[0],mandatory:'true'},input.criteria[1]]}),/Mandatory must be a boolean/);checks++;
assert.throws(()=>exportEvidenceCoverageCSV({...result,ratings:[{...result.ratings[0],evidenceRef:'=HYPERLINK("evil")'},...result.ratings.slice(1)]}),/CSV export blocked/);checks++;
assert.throws(()=>exportEvidenceCoverageCSV({...result,vendors:[{...result.vendors[0],priceCents:NaN},result.vendors[1]]}),/Invalid saved price cents/);checks++;
const forged={...result,comparisons:[{...result.comparisons[0],scorePercent:100}]};
eq(exportEvidenceCoverageCSV(forged),csv);
console.log('PASS: '+checks+' evidence coverage and provenance assertions');
