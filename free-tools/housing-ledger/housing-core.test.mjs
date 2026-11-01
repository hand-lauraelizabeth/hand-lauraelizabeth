import assert from 'node:assert/strict';
import {buildHousingLedger,exportHousingJSON} from './housing-core.mjs';
let count=0;const check=(f)=>{f();count++;};
const source={sourceId:'00001',kind:'receipt',label:'Synthetic receipt',date:'2026-10-01'};
const event={eventId:'evt-01',date:'2026-10-02',category:'deposit',description:'Synthetic deposit',sourceIds:['00001'],amountCents:null};
const ledger=buildHousingLedger({sources:[source],events:[event]});
check(()=>assert.equal(ledger.events[0].sourceIds[0],'00001'));
check(()=>assert.deepEqual(ledger.findings,[{eventId:'evt-01',kind:'missing-deposit-amount'}]));
check(()=>assert.equal(JSON.parse(exportHousingJSON(ledger)).sources[0].sourceId,'00001'));
check(()=>assert.equal(source.sourceId,'00001'));
for(const [name,change] of [
 ['duplicate-source',()=>({sources:[source,source],events:[]})],
 ['unknown-source',()=>({sources:[source],events:[{...event,sourceIds:['missing']}]})],
 ['duplicate-event',()=>({sources:[source],events:[event,event]})],
 ['invalid-date',()=>({sources:[source],events:[{...event,date:'2026-02-30'}]})],
 ['invalid-amount',()=>({sources:[source],events:[{...event,amountCents:0.5}]})],
 ['unsafe-id',()=>({sources:[{...source,sourceId:'=1\u0000'}],events:[]})],
 ['excessive-links',()=>({sources:[source],events:[{...event,sourceIds:Array.from({length:31},(_,i)=>String(i))}]})]
])check(()=>assert.throws(()=>buildHousingLedger(change()),undefined,name));
for(let seed=0;seed<200;seed++){const id=`00${seed}-Δ`;const d=`2026-10-${String(seed%28+1).padStart(2,'0')}`;const out=buildHousingLedger({sources:[{...source,sourceId:id}],events:[{...event,eventId:`e${seed}`,date:d,sourceIds:[id],amountCents:seed}]});check(()=>assert.equal(JSON.parse(exportHousingJSON(out)).events[0].sourceIds[0],id));check(()=>assert.equal(out.findings.length,0));}
// A valid ledger near the import ceiling must still be exportable byte-for-byte.
const near=buildHousingLedger({sources:[],events:Array.from({length:1999},(_,i)=>({
  eventId:'near-'+i,date:'2026-10-01',category:'repair',
  description:'é'.repeat(1129),sourceIds:[],amountCents:null
}))});
check(()=>assert.ok(Buffer.byteLength(exportHousingJSON(near),'utf8')<=5_000_000));
check(()=>assert.ok(Buffer.byteLength(exportHousingJSON(near),'utf8')>4_990_000));
const tooLarge=buildHousingLedger({sources:[],events:[...near.events,{
  eventId:'overflow',date:'2026-10-02',category:'repair',
  description:'é'.repeat(2000),sourceIds:[],amountCents:null
}]});
check(()=>assert.throws(()=>exportHousingJSON(tooLarge),/5,000,000-byte reopen limit/));
check(()=>assert.throws(()=>exportHousingJSON(buildHousingLedger({sources:[],events:
  Array.from({length:2000},(_,i)=>({eventId:'huge-'+i,date:'2026-10-01',
    category:'repair',description:'é'.repeat(1400),sourceIds:[],amountCents:null}))
})),/5,000,000-byte reopen limit/));
console.log(`PASS: ${count} FT-12 Node assertions`);
