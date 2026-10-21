import assert from 'node:assert/strict';
import {filterReviewRows, reviewStatusSummary, REVIEW_STATUSES} from './review-filter.mjs';
import {normalizeExact} from './exact-core.mjs';
import {exportEvidenceCSV} from './core.mjs';

// Deterministic, synthetic-only test of filtering against an independent oracle.
let state=0x17a0bcd1;
const next=()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state;};
const idParts=['000123','caf\u00e9','cafe\u0301','=SUM(1,2)','+11','-2','@user','\t=FORMULA','line\nbreak','ABC'];
let assertions=0;
const check=(actual,expected,label)=>{assert.deepEqual(actual,expected,label);assertions++;};
for(let scenario=0;scenario<300;scenario++){
 const size=next()%41;
 const rows=[];
 for(let j=0;j<size;j++){
   const sourceId=`${scenario.toString(36)}:${j.toString().padStart(3,'0')}:${idParts[next()%idParts.length]}`;
   rows.push({sourceId,date:'2026-10-17',kind:'source',status:REVIEW_STATUSES[next()%4],claim:'Synthetic '+sourceId,group:''});
 }
 const normalized=normalizeExact(rows);
 const before=JSON.stringify(normalized);
 const csvBefore=exportEvidenceCSV(normalized);
 const counts={reported:0,corroborated:0,disputed:0,unresolved:0};
 for(const row of normalized) counts[row.status]++;
 const expectedSummary=`Reported: ${counts.reported} · Corroborated: ${counts.corroborated} · Disputed: ${counts.disputed} · Unresolved: ${counts.unresolved}. Statuses are user-assigned.`;
 check(reviewStatusSummary(normalized),expectedSummary,`summary scenario ${scenario}`);
 for(const status of ['all',...REVIEW_STATUSES]){
   const expected=normalized.filter(row=>status==='all'||row.status===status).map(row=>row.sourceId);
   const actual=filterReviewRows(normalized,status);
   check(actual.map(row=>row.sourceId),expected,`IDs scenario ${scenario}/${status}`);
   check(actual.length,expected.length,`length scenario ${scenario}/${status}`);
   check(actual===normalized,false,`new array scenario ${scenario}/${status}`);
 }
 check(JSON.stringify(normalized),before,`immutability scenario ${scenario}`);
 check(exportEvidenceCSV(normalized),csvBefore,`full export unchanged scenario ${scenario}`);
 check(Object.values(counts).reduce((a,b)=>a+b,0),size,`partition scenario ${scenario}`);
}
assert.throws(()=>filterReviewRows([], 'UNVERIFIED'),/Unknown review status/);assertions++;
assert.throws(()=>reviewStatusSummary([{status:'unverified'}]),/Unknown record status/);assertions++;
console.log(`PASS: ${assertions} deterministic synthetic property assertions across 300 scenarios`);
