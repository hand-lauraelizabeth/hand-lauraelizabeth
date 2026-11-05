import assert from 'node:assert/strict';
import {normalizeExact} from './exact-core.mjs';
import {changeReviewStatus,undoReviewStatus} from './undo-status.mjs';
import {csvExportRisk} from './safe-export.mjs';
const original=normalizeExact([
 {sourceId:'000123',date:'2026-10-25',claim:'Synthetic café — résumé',status:'reported',kind:'source',group:'α'},
 {sourceId:'000456',date:'2026-10-24',claim:'Synthetic second',status:'unresolved',kind:'observation',group:''}
]);
let checks=0;
const check=(value,label)=>{assert.ok(value,label);checks++;};
const snapshot=JSON.stringify(original);
const changed=changeReviewStatus(original,'000123','disputed');
check(changed.records.find(r=>r.sourceId==='000123').status==='disputed','status updated');
check(changed.undo.sourceId==='000123' && changed.undo.before==='reported' && changed.undo.after==='disputed','undo identity and transitions');
check(Object.isFrozen(changed.undo),'undo descriptor frozen');
check(JSON.stringify(original)===snapshot,'original immutable');
check(changed.records.find(r=>r.sourceId==='000456').status==='unresolved','unrelated status retained');
const restored=undoReviewStatus(changed.records,changed.undo);
check(JSON.stringify(restored)===snapshot,'undo restores exact original records');
check(restored!==original && restored!==changed.records,'immutable undo');
check(csvExportRisk(restored)===null,'CSV gate unchanged');
check(changeReviewStatus(original,'000123','reported').undo===null,'no-op does not offer undo');
assert.throws(()=>undoReviewStatus(original,changed.undo),/no longer available/);checks++;
assert.throws(()=>undoReviewStatus([],changed.undo),/no longer available/);checks++;
assert.throws(()=>undoReviewStatus(changed.records,{...changed.undo,before:'INVALID'}),/Invalid undo/);checks++;
assert.throws(()=>changeReviewStatus(original,'000123','INVALID'),/Invalid review status/);checks++;
assert.throws(()=>changeReviewStatus(original,'123','disputed'),/Source ID not found/);checks++;
const hostile=normalizeExact([{sourceId:'=1+1',date:'2026-10-25',claim:'Synthetic =SUM(1,1)',status:'reported'}]);
const unsafe=changeReviewStatus(hostile,'=1+1','corroborated');
check(undoReviewStatus(unsafe.records,unsafe.undo)[0].sourceId==='=1+1','exact formula-like ID');
check(Boolean(csvExportRisk(undoReviewStatus(unsafe.records,unsafe.undo))),'unsafe CSV still blocked');
console.log('PASS: '+checks+' synthetic immutable undo and evidence-safety assertions');
