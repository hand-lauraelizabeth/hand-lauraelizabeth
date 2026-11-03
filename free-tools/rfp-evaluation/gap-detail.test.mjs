import test from 'node:test';
import assert from 'node:assert/strict';
import {evaluateWithProvenance} from './evidence-coverage.mjs';
import {listEvidenceGaps} from './gap-detail.mjs';

const base=()=>({
 criteria:[{id:'C-1',label:'Delivery',weight:'100',sourceRef:'REQ-1',mandatory:false}],
 vendors:[{id:'V-1',name:'Fictional vendor',price:'12.00',conflict:'none'}],
 ratings:[{vendorId:'V-1',criterionId:'C-1',score:'0',evidenceRef:'EV-1',reviewer:'QA',note:''}]
});
test('complete pair including zero score produces no gap or vendor decision',()=>{
 const result=evaluateWithProvenance(base());
 assert.deepEqual(listEvidenceGaps(result),[]);
 assert.equal(result.comparisons[0].scorePercent,0);
});
test('missing score is distinguished from missing source, and exact IDs survive',()=>{
 const data=base();data.ratings=[];data.criteria[0].sourceRef='';
 const gaps=listEvidenceGaps(evaluateWithProvenance(data));
 assert.equal(gaps.length,1);
 assert.equal(gaps[0].vendorId,'V-1');assert.equal(gaps[0].criterionId,'C-1');
 assert.equal(gaps[0].score,null);
 assert.deepEqual(gaps[0].issues,['Score missing','Criterion source missing']);
});
test('scored but missing reviewer/evidence flags both without changing score',()=>{
 const data=base();data.ratings[0].reviewer='';data.ratings[0].evidenceRef='';
 const result=evaluateWithProvenance(data);const gaps=listEvidenceGaps(result);
 assert.equal(gaps.length,1);assert.equal(gaps[0].score,0);
 assert.deepEqual(gaps[0].issues,['Evidence reference missing','Reviewer identifier missing']);
 assert.equal(result.ratings[0].score,0);
});
test('invisible references are not counted as evidence; exact values are retained',()=>{
 const data=base();data.criteria[0].sourceRef='\u200b';data.ratings[0].evidenceRef='\u0301';data.ratings[0].reviewer='\u2066';
 const gaps=listEvidenceGaps(evaluateWithProvenance(data));
 assert.equal(gaps.length,1);
 assert.equal(gaps[0].criterionSourceRef,'\u200b');
 assert.equal(gaps[0].evidenceRef,'\u0301');
 assert.equal(gaps[0].reviewer,'\u2066');
 assert.equal(gaps[0].issues.length,3);
});
test('vendor/criterion order and raw HTML-looking IDs are preserved, never interpreted',()=>{
 const data=base();data.criteria=[
  {id:'<img src=x onerror=alert(1)>',label:'First',weight:'40',sourceRef:'REQ-1',mandatory:false},
  {id:'C-2',label:'Second',weight:'60',sourceRef:'REQ-2',mandatory:false}
 ];data.vendors=[data.vendors[0],{id:'V-2',name:'Other',price:'',conflict:'unreviewed'}];data.ratings=[];
 const gaps=listEvidenceGaps(evaluateWithProvenance(data));
 assert.equal(gaps.length,4);
 assert.deepEqual(gaps.map(g=>[g.vendorId,g.criterionId]),[
  ['V-1','<img src=x onerror=alert(1)>'],['V-1','C-2'],
  ['V-2','<img src=x onerror=alert(1)>'],['V-2','C-2']
 ]);
 assert.ok(Object.isFrozen(gaps)&&Object.isFrozen(gaps[0])&&Object.isFrozen(gaps[0].issues));
});
test('maximum 30 by 30 pairs remains bounded at 900 unresolved rows',()=>{
 const data={criteria:Array.from({length:30},(_,i)=>({id:'C'+i,label:'Criterion',weight:String(i===0?100:0),sourceRef:'S'+i,mandatory:false})),
 vendors:Array.from({length:30},(_,i)=>({id:'V'+i,name:'Vendor',price:'',conflict:'unreviewed'})),ratings:[]};
 const gaps=listEvidenceGaps(evaluateWithProvenance(data));
 assert.equal(gaps.length,900);
 assert.equal(gaps[0].vendorId,'V0');assert.equal(gaps[899].criterionId,'C29');
});
test('malformed comparison structure is rejected rather than guessed',()=>{
 const result=evaluateWithProvenance(base());
 assert.throws(()=>listEvidenceGaps({...result,comparisons:[]}),/Invalid evaluated/);
});
