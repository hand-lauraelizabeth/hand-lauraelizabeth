import assert from 'node:assert/strict';
import {project,exportJSON} from './engine.mjs';

// Synthetic-only regression: the opening balance is a starting input, not
// necessarily an observed projected end-of-day balance.
const event=(id,date,cents)=>({id,label:id,date,repeat:'once',cents});
const start='2026-10-25',end='2026-10-27';
let passed=0;
function check(label,fn){fn();passed++;console.log('PASS '+label)}
const rising=project({start,end,openingCents:10000,events:[
  event('pay','2026-10-25',5000),event('refund','2026-10-26',2000)
]});
check('rising daily balances',()=>assert.deepEqual(rising.days.map(d=>d.balanceCents),[15000,17000,17000]));
check('rising minimum uses first observed end of day',()=>assert.equal(rising.minimumCents,15000));
check('rising minimum date is actual observed day',()=>assert.equal(rising.minimumDate,start));
const recovery=project({start,end,openingCents:-1000,events:[event('pay','2026-10-25',2000)]});
check('opening deficit not falsely called end-of-day minimum',()=>assert.equal(recovery.minimumCents,1000));
check('recovery minimum date',()=>assert.equal(recovery.minimumDate,start));
const falling=project({start,end,openingCents:10000,events:[event('bill','2026-10-26',-11000)]});
check('genuine negative day still detected',()=>assert.equal(falling.minimumCents,-1000));
check('genuine negative date',()=>assert.equal(falling.minimumDate,'2026-10-26'));
const flat=project({start,end,openingCents:500,events:[]});
check('flat balance minimum is opening balance',()=>assert.equal(flat.minimumCents,500));
check('minimum equals independent daily-balance oracle',()=>{
 for(const p of [rising,recovery,falling,flat]){
  const min=Math.min(...p.days.map(d=>d.balanceCents));
  assert.equal(p.minimumCents,min);
  assert.equal(p.minimumDate,p.days.find(d=>d.balanceCents===min).date);
 }
});
check('JSON exported minimum matches independent oracle',()=>{
 const json=JSON.parse(exportJSON(rising));
 assert.equal(json.minimumCents,Math.min(...json.days.map(d=>d.balanceCents)));
});
console.log('PASS '+passed+' FT-04 end-of-day minimum assertions');
