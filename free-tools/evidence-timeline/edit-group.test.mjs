import assert from 'node:assert/strict';
import {normalizeExact} from './exact-core.mjs';
import {setReviewGroup} from './edit-group.mjs';
import {summary} from './core.mjs';
const source = normalizeExact([
  {sourceId:'0001',date:'2026-10-24',claim:'First synthetic record',group:'',status:'reported'},
  {sourceId:'cafe\u0301',date:'2026-10-25',claim:'Unicode record',group:'other',status:'disputed'},
  {sourceId:'=SUM(A1)',date:'2026-10-26',claim:'Literal formula-like ID',group:'other',status:'unresolved'}
]);
let n=0;function check(condition,label){assert.ok(condition,label);n++;}
const original=JSON.stringify(source);
let updated=setReviewGroup(source,'0001','other');
check(updated.length===3,'record count retained');
check(updated[0].sourceId==='0001','exact source ID retained');
check(updated[0].group==='other','group assigned');
check(updated[0].claim===source[0].claim && updated[0].date===source[0].date,'evidence preserved');
check(updated[1].group==='other' && updated[2].group==='other','other records unchanged');
check(summary(updated).reviewGroups[0].sourceIds.length===3,'related-record group appears');
check(JSON.stringify(source)===original,'original ledger not mutated');
check(updated!==source && updated[0]!==source[0],'immutable records');
updated=setReviewGroup(updated,'cafe\u0301','new\u00a0group');
check(updated[1].group==='new\u00a0group','Unicode whitespace preserved');
check(updated[1].sourceId==='cafe\u0301','decomposed source ID preserved');
updated=setReviewGroup(updated,'=SUM(A1)','');
check(updated[2].group==='' && updated[2].sourceId==='=SUM(A1)','group cleared, formula-like source ID unchanged');
updated=setReviewGroup(updated,'0001','=1+1');
check(updated[0].group==='=1+1','formula-risk group preserved for JSON; CSV separately gated');
for(const [id,group,pattern] of [
  ['missing','x',/Source ID not found/],
  [null,'x',/Invalid related-record/],
  ['0001',null,/Invalid related-record/],
  ['0001','x'.repeat(121),/Invalid related-record/]
]){assert.throws(()=>setReviewGroup(source,id,group),pattern);n++;}
assert.throws(()=>setReviewGroup(source.map((r,i)=>i===1?{...r,sourceId:'0001'}:r),'0001','x'),/duplicate source ID/);n++;
check(JSON.stringify(source)===original,'failed edits preserve original evidence');
const bulk=Array.from({length:10000},(_,i)=>({
  sourceId:'S-'+String(i).padStart(5,'0'),date:'2026-10-24',
  claim:'Synthetic '+i,status:'reported',kind:'source',group:''
}));
const changed=setReviewGroup(bulk,'S-09999','batch');
check(changed.length===10000 && changed[9999].group==='batch','10k-record limit');
check(changed[0].group==='' && bulk[9999].group==='','10k other records and original unchanged');
assert.throws(()=>setReviewGroup([...bulk,bulk[0]],'S-09999','x'),/At most 10000/);n++;
console.log('PASS: '+n+' related-record group edit and evidence integrity assertions');
