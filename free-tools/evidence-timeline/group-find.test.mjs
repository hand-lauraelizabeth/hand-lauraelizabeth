import assert from 'node:assert/strict';
import {normalizeExact} from './exact-core.mjs';
import {filterByGroupLabel} from './group-find.mjs';
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
check(filterByGroupLabel(records).length===5,'empty query includes grouped and ungrouped');
check(filterByGroupLabel(records,'café').map(r=>r.sourceId).join()==='0001','composed Unicode exact');
check(filterByGroupLabel(records,'cafe\u0301').map(r=>r.sourceId).join()==='0002','decomposed Unicode exact');
check(filterByGroupLabel(records,'CAFÉ').map(r=>r.sourceId).join()==='0005','case preserved');
check(filterByGroupLabel(records,'cafe').length===1,'no Unicode normalization');
check(filterByGroupLabel(records,'caf').length===2,'literal substring matches both Unicode spellings');
check(filterByGroupLabel(records,'=SUM(A1)')[0].sourceId==='0004','formula-like group treated literally');
check(filterByGroupLabel(records,'',true).map(r=>r.sourceId).join()==='0003','ungrouped only');
check(filterByGroupLabel(records,'café',true).map(r=>r.sourceId).join()==='0003','ungrouped toggle takes precedence');
check(filterByGroupLabel(findSourceIds(records,'disputed','0002'),'cafe\u0301').length===1,'status/source/group intersection');
check(filterByGroupLabel(findSourceIds(records,'reported','0002'),'cafe\u0301').length===0,'status intersection can be empty');
check(filterByGroupLabel(records,'unknown').length===0,'no-match');
check(JSON.stringify(records)===original,'never changes evidence');
check(filterByGroupLabel(records)!==records,'result is separate array');
for(const [rows,q,flag] of [[{},'',false],[records,null,false],[records,'x'.repeat(121),false],[records,'',null],[records.map((r,i)=>i===0?{...r,group:null}:r),'',false]]) {
 assert.throws(()=>filterByGroupLabel(rows,q,flag),/Invalid group search/);n++;
}
const bulk=Array.from({length:10000},(_,i)=>({group:i%2?'batch':'',sourceId:'S-'+i}));
check(filterByGroupLabel(bulk,'batch').length===5000,'10k grouped boundary');
check(filterByGroupLabel(bulk,'',true).length===5000,'10k ungrouped boundary');
assert.throws(()=>filterByGroupLabel([...bulk,bulk[0]]),/Invalid group search records/);n++;
console.log('PASS: '+n+' group-filter integrity assertions');
