import assert from 'node:assert/strict';
import {normalizeExact} from './exact-core.mjs';
import {updateReviewStatus, STATUS_OPTIONS} from './reclassify.mjs';
import {csvExportRisk} from './safe-export.mjs';

const original=normalizeExact([
  {sourceId:'000123',date:'2026-10-25',claim:'Synthetic café — résumé',status:'reported',kind:'source',group:'α'},
  {sourceId:'000456',date:'2026-10-24',claim:'Synthetic second',status:'reported',kind:'observation',group:''}
]);
const snapshot=JSON.stringify(original);
let checks=0;
function check(condition,message){assert.ok(condition,message);checks++;}
check(STATUS_OPTIONS.join(',')==='reported,corroborated,disputed,unresolved','fixed review statuses');
for(const status of STATUS_OPTIONS){
  const next=updateReviewStatus(original,'000123',status);
  check(next.find(x=>x.sourceId==='000123').status===status,'selected status '+status);
  check(next.find(x=>x.sourceId==='000123').claim==='Synthetic café — résumé','exact Unicode evidence');
  check(next.find(x=>x.sourceId==='000456').status==='reported','unrelated status retained');
  check(next.map(x=>x.sourceId).join(',')==='000456,000123','chronology retained');
  check(csvExportRisk(next)===null,'safe CSV unaffected');
}
check(JSON.stringify(original)===snapshot,'original immutable');
check(updateReviewStatus(original,'000123','disputed')!==original,'new array');
for(const bad of ['unknown','',null,'CORROBORATED','__proto__']){
  assert.throws(()=>updateReviewStatus(original,'000123',bad),/Invalid review status/);checks++;
}
for(const id of ['123','000124','000123 ','__proto__']){
  assert.throws(()=>updateReviewStatus(original,id,'disputed'),/Source ID not found/);checks++;
}
assert.throws(()=>updateReviewStatus([{...original[0]},{...original[0]}],'000123','disputed'),/duplicate source ID/i);checks++;
assert.throws(()=>updateReviewStatus([], '000123','disputed'),/Source ID not found/);checks++;
const hostile=normalizeExact([{sourceId:'=1+1',date:'2026-10-25',claim:'exact formula-like evidence',status:'reported'}]);
const updated=updateReviewStatus(hostile,'=1+1','unresolved');
check(updated[0].sourceId==='=1+1','unsafe exact ID remains exact');
check(Boolean(csvExportRisk(updated)),'unsafe CSV remains blocked');
check(JSON.stringify(hostile)!==JSON.stringify(updated),'status changed');
console.log('PASS: '+checks+' immutable status, exact ID, invalid-input and CSV safety assertions');
