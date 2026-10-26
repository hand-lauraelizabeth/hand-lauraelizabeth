import test from 'node:test';
import assert from 'node:assert/strict';
import {evaluateWithProvenance} from './evidence-coverage.mjs';
import {summarizeCoverage,describeCoverage} from './coverage-summary.mjs';

// Synthetic records only. A zero score is not missing.
const base={
 criteria:[{id:'C-01',label:'Delivery',weight:60,sourceRef:'REQ-01',mandatory:true},
           {id:'C-02',label:'Support',weight:40,sourceRef:'REQ-02',mandatory:false}],
 vendors:[{id:'V-01',name:'Vendor one',price:'20.00',conflict:'none'},
          {id:'V-02',name:'Vendor two',price:'',conflict:'unreviewed'}],
 ratings:[{vendorId:'V-01',criterionId:'C-01',score:0,evidenceRef:'EV-01'},
          {vendorId:'V-01',criterionId:'C-02',score:5,evidenceRef:'EV-02'},
          {vendorId:'V-02',criterionId:'C-01',score:'',evidenceRef:''},
          {vendorId:'V-02',criterionId:'C-02',score:4,evidenceRef:''}]
};
test('counts zero as scored and missing as missing, without manufacturing a score',()=>{
 const result=evaluateWithProvenance(base);
 assert.deepEqual(summarizeCoverage(result),{
  totalPairs:4,scoredPairs:3,documentedPairs:2,missingScores:1,
  scoredWithoutReferences:1,withheld:1,conflictReview:1,missingPrices:1
 });
 assert.equal(result.comparisons[1].scorePercent,null);
 assert.match(describeCoverage(result),/3 of 4 vendor–criterion pairs scored/);
 assert.match(describeCoverage(result),/not an award decision/);
});
test('criterion source omission reduces documented coverage without changing scores',()=>{
 const input={...base,criteria:base.criteria.map((c,i)=>i===0?{...c,sourceRef:''}:c)};
 const result=evaluateWithProvenance(input),summary=summarizeCoverage(result);
 assert.equal(summary.scoredPairs,3);
 assert.equal(summary.documentedPairs,1);
 assert.equal(summary.scoredWithoutReferences,2);
 assert.equal(summary.withheld,2);
});
test('visually empty Unicode references do not count as documented',()=>{
 const input={...base,ratings:base.ratings.map((r,i)=>i===0?{...r,evidenceRef:'\u200b\u0301'}:r)};
 const summary=summarizeCoverage(evaluateWithProvenance(input));
 assert.equal(summary.scoredPairs,3);
 assert.equal(summary.documentedPairs,1);
 assert.equal(summary.withheld,2);
});
test('complete evidence counts all pairs, no withholding',()=>{
 const input={...base,vendors:base.vendors.map(v=>({...v,conflict:'none',price:'1.00'})),
 ratings:base.ratings.map(r=>({...r,score:0,evidenceRef:'EV-00'}))};
 const summary=summarizeCoverage(evaluateWithProvenance(input));
 assert.deepEqual(summary,{totalPairs:4,scoredPairs:4,documentedPairs:4,missingScores:0,scoredWithoutReferences:0,withheld:0,conflictReview:0,missingPrices:0});
});
test('invalid external coverage cannot be silently summarized',()=>{
 const result=evaluateWithProvenance(base);
 assert.throws(()=>summarizeCoverage({...result,comparisons:[{...result.comparisons[0],detail:[]}]}),/Invalid evaluated RFP coverage|Invalid evaluated RFP details/);
 assert.throws(()=>summarizeCoverage({...result,comparisons:result.comparisons.map(v=>({...v,detail:[{...v.detail[0],criterionId:'other'},...v.detail.slice(1)]}))}),/criterion reference/);
});
