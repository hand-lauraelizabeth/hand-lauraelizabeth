import assert from 'node:assert/strict';
import {normalizeExact} from './exact-core.mjs';
import {findSourceIds} from './source-id-find.mjs';
const rows=normalizeExact([
  {sourceId:'000123',date:'2026-10-24',claim:'Synthetic one',status:'reported'},
  {sourceId:'ABC-000123',date:'2026-10-25',claim:'Synthetic two',status:'disputed'},
  {sourceId:'café',date:'2026-10-26',claim:'Synthetic three',status:'unresolved'},
  {sourceId:'cafe\u0301',date:'2026-10-27',claim:'Synthetic four',status:'reported'},
  {sourceId:'=1+1',date:'2026-10-27',claim:'Synthetic five',status:'reported'}
]);
let n=0;const check=(v,label)=>{assert.ok(v,label);n++;};
const snapshot=JSON.stringify(rows);
check(findSourceIds(rows).length===5,'empty query retains all');
check(findSourceIds(rows,'all','000123').length===2,'literal substring finds both IDs');
check(findSourceIds(rows,'reported','000123').map(x=>x.sourceId).join('|')==='000123','status intersection');
check(findSourceIds(rows,'all','ABC').map(x=>x.sourceId).join('|')==='ABC-000123','case-sensitive exact match');
check(findSourceIds(rows,'all','abc').length===0,'no case folding');
check(findSourceIds(rows,'all',' 000123').length===0,'no silent trimming');
check(findSourceIds(rows,'all','café').map(x=>x.sourceId).join('|')==='café','composed Unicode exact');
check(findSourceIds(rows,'all','cafe\u0301').map(x=>x.sourceId).join('|')==='cafe\u0301','decomposed Unicode exact');
check(findSourceIds(rows,'all','=1+1')[0].sourceId==='=1+1','formula-like ID remains literal');
check(findSourceIds(rows,'all','no match').length===0,'empty results');
check(JSON.stringify(rows)===snapshot,'source rows unchanged');
check(findSourceIds(rows)!==rows,'results are separate array');
assert.throws(()=>findSourceIds(rows,'all',null),/Invalid source ID/);n++;
assert.throws(()=>findSourceIds(rows,'all','x'.repeat(121)),/Invalid source ID/);n++;
assert.throws(()=>findSourceIds(rows,'bogus',''),/Unknown review status/);n++;
assert.throws(()=>findSourceIds({},'all',''),/Invalid record list/);n++;
const bulk=Array.from({length:10000},(_,i)=>({sourceId:'S-'+String(i).padStart(5,'0'),status:'reported'}));
check(findSourceIds(bulk,'reported','S-09999').length===1,'10k literal search boundary');
check(findSourceIds(bulk,'reported','S-').length===10000,'10k all-match boundary');
console.log('PASS: '+n+' source-ID search and evidence-integrity assertions');
