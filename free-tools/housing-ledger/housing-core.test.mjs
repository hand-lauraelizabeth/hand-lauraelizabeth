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
console.log(`PASS: ${count} FT-12 Node assertions`);
