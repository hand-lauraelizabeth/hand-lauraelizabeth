import assert from 'node:assert/strict';
import {normalizeEvidence,findReviewGroups,exportEvidenceCSV,summary} from './core.mjs';
import {normalizeExact} from './exact-core.mjs';
let n=0;
const eq=(a,b)=>{assert.deepEqual(a,b);n++;};
const bad=(fn)=>{assert.throws(fn);n++;};
const rec=(id,extra={})=>({sourceId:id,date:'2026-10-15',claim:'  Synthetic claim\nnext line  ',status:'reported',kind:'source',group:' G ',...extra});
const source=[rec(' ID '),rec('ID',{date:'2026-10-14'}),rec('Ω',{group:' G ',status:'disputed'})];
const actual=normalizeEvidence(source);
eq(actual,normalizeExact(source));
eq(actual.map(x=>x.sourceId),['ID',' ID ','Ω']);
eq(actual[1].claim,'  Synthetic claim\nnext line  ');
eq(actual[1].group,' G ');
eq(actual[1].sourceId,' ID ');
eq(actual[2].sourceId,'Ω');
eq(source[0].sourceId,' ID ');
eq(findReviewGroups(actual)[0].sourceIds,['ID',' ID ','Ω']);
eq(summary(actual).counts.disputed,1);
eq(exportEvidenceCSV(actual).includes('"  Synthetic claim\nnext line  "'),true);
for(const [id,extra] of [
 [' ' ,{}],['X',{claim:' '}],['X',{sourceId:42}],['X',{claim:42}],
 ['X',{group:'z'.repeat(121)}],['X',{claim:'z'.repeat(20001)}],
 ['X',{date:'2025-02-29'}],['X',{date:'0000-01-01'}],['X',{date:'2026-13-01'}],
 ['X',{status:'approved'}],['X',{kind:'judgment'}]
])bad(()=>normalizeEvidence([rec(id,extra)]));
bad(()=>normalizeEvidence([rec('A'),rec('A')]));
eq(normalizeEvidence([rec(' ID '),rec('ID')]).length,2);
eq(normalizeEvidence([rec('A',{date:'0004-02-29'})])[0].date,'0004-02-29');
const formula=['=1+1','+2','-3','@SUM(1)',' \t=2','\uFEFF=3','＝1+1','＋1','－1','＠SUM(1)',' \t＝1'];
for(const claim of formula)eq(exportEvidenceCSV([rec('X',{claim})]).includes('"\''+claim+'"'),true);
eq(exportEvidenceCSV(actual).endsWith('\r\n'),true);
console.log(n+' legacy exact-field, rejection, grouping and CSV assertions PASS');
