import assert from 'node:assert/strict';
import {buildHousingLedger,reviseHousingEvent,exportHousingJSON} from './housing-core.mjs';
let n=0;const check=fn=>{fn();n++;};
const sources=[
  {sourceId:'000-Δ/１',kind:'receipt',label:'Synthetic <script>alert(1)</script>',date:'2026-10-01'},
  {sourceId:'002',kind:'email',label:'Synthetic evidence',date:null}
];
const events=[
  {eventId:'E-000',date:'2026-10-03',category:'deposit',description:'Original\r\n=1+1',sourceIds:[],amountCents:null},
  {eventId:'E-002',date:'2026-10-04',category:'rent',description:'Unrelated',sourceIds:['002'],amountCents:150000}
];
const before=buildHousingLedger({sources,events});
const original=exportHousingJSON(before);
const patch={date:'2026-10-02',description:'Original\r\n=1+1',sourceIds:['000-Δ/１'],amountCents:0};
const after=reviseHousingEvent({sources:before.sources,events:before.events},'E-000',patch);
check(()=>assert.equal(after.events[0].eventId,'E-000'));
check(()=>assert.equal(after.events[0].date,'2026-10-02'));
check(()=>assert.equal(after.events[0].amountCents,0));
check(()=>assert.equal(after.events[0].description,'Original\r\n=1+1'));
check(()=>assert.deepEqual(after.events[0].sourceIds,['000-Δ/１']));
check(()=>assert.deepEqual(after.events[1],before.events[1]));
check(()=>assert.deepEqual(after.sources,before.sources));
check(()=>assert.deepEqual(after.findings,[]));
check(()=>assert.equal(exportHousingJSON(before),original));
check(()=>assert.equal(JSON.parse(exportHousingJSON(after)).events[0].amountCents,0));
const errors=[
 ['unknown-id','E-NO',patch],
 ['wrong-shape','E-000',{date:'2026-10-02'}],
 ['forged-id','E-000',{...patch,eventId:'FORGED'}],
 ['invalid-date','E-000',{...patch,date:'2026-02-30'}],
 ['missing-link','E-000',{...patch,sourceIds:['missing']}],
 ['duplicate-link','E-000',{...patch,sourceIds:['002','002']}],
 ['fractional-cents','E-000',{...patch,amountCents:0.5}],
 ['negative-cents','E-000',{...patch,amountCents:-1}],
 ['oversize-cents','E-000',{...patch,amountCents:100000000001}],
 ['invalid-text','E-000',{...patch,description:'bad\u0000'}],
 ['unexpected-field','E-000',{...patch,category:'repair'}],
];
for(const [label,id,changes] of errors)check(()=>assert.throws(
 ()=>reviseHousingEvent({sources:before.sources,events:before.events},id,changes),undefined,label
));
check(()=>assert.equal(exportHousingJSON(before),original));
console.log('PASS: '+n+' FT-12 atomic event correction assertions');
