import assert from 'node:assert/strict';
import {normalizeExact} from './exact-core.mjs';
import {findReviewGroups} from './group-find.mjs';
import {findSourceIds} from './source-id-find.mjs';
let n=0; const check=(value,label)=>{assert.ok(value,label);n++;};
const records=normalizeExact([
 {sourceId:'0001',date:'2026-10-24',claim:'Synthetic A',group:'café',status:'reported'},
 {sourceId:'0002',date:'2026-10-25',claim:'Synthetic B',group:'cafe\u0301',status:'disputed'},
 {sourceId:'0003',date:'2026-10-26',claim:'Synthetic C',group:'',status:'reported'},
 {sourceId:'0004',date:'2026-10-27',claim:'Synthetic D',group:'=SUM(A1)',status:'unresolved'},
 {sourceId:'0005',date:'2026-10-27',claim:'Synthetic E',group:'CAFÉ',status:'reported'}
]);
const original=JSON.stringify(records);
check(findReviewGroups(records).length===5,'empty query includes grouped and ungrouped');
check(findReviewGroups(records,'café').map(r=>r.sourceId).join()==='0001','composed Unicode exact');
check(findReviewGroups(records,'cafe\u0301').map(r=>r.sourceId).join()==='0002','decomposed Unicode exact');
check(findReviewGroups(records,'CAFÉ').map(r=>r.sourceId).join()==='0005','case preserved');
check(findReviewGroups(records,'cafe').length===1,'no Unicode normalization');
check(findReviewGroups(records,'caf').length===1,'literal substring');
check(findReviewGroups(records,'=SUM(A1)')[0].sourceId==='0004','formula-like group treated literally');
check(findReviewGroups(records,'',true).map(r=>r.sourceId).join()==='0003','ungrouped only');
check(findReviewGroups(records,'café',true).map(r=>r.sourceId).join()==='0003','ungrouped toggle takes precedence');
check(findReviewGroups(findSourceIds(records,'disputed','0002'),'cafe\u0301').length===1,'status/source/group intersection');
check(findReviewGroups(findSourceIds(records,'reported','0002'),'cafe\u0301').length===0,'status intersection can be empty');
check(findReviewGroups(records,'unknown').length===0,'no-match');
check(JSON.stringify(records)===original,'never changes evidence');
check(findReviewGroups(records)!==records,'result is separate array');
for(const [rows,q,flag] of [[{},'',false],[records,null,false],[records,'x'.repeat(121),false],[records,'',null],[records.map((r,i)=>i===0?{...r,group:null}:r),'',false]]) {
 assert.throws(()=>findReviewGroups(rows,q,flag),/Invalid group search/);n++;
}
const bulk=Array.from({length:10000},(_,i)=>({group:i%2?'batch':'',sourceId:'S-'+i}));
check(findReviewGroups(bulk,'batch').length===5000,'10k grouped boundary');
check(findReviewGroups(bulk,'',true).length===5000,'10k ungrouped boundary');
assert.throws(()=>findReviewGroups([...bulk,bulk[0]]),/Invalid group search records/);n++;
console.log('PASS: '+n+' group-filter integrity assertions');
