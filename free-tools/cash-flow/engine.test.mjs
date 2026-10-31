import assert from 'node:assert/strict';
import {dateUTC,addDays,parseCents,formatCents,occurrences,project,csvCell,exportCSV,csvExportRisk,exportSafeCSV,exportJSON} from './engine.mjs';
let n=0;const check=(fn)=>{fn();n++};
check(()=>assert.equal(addDays('2024-02-28',1),'2024-02-29'));
check(()=>assert.equal(addDays('2024-02-29',1),'2024-03-01'));
for(const bad of ['2026-02-29','2026-13-01','2026-04-31','10/14/2026'])check(()=>assert.throws(()=>dateUTC(bad)));
check(()=>assert.equal(parseCents('100.09'),10009));
check(()=>assert.equal(parseCents('-0.01'),-1));
check(()=>assert.equal(formatCents(-1),'-0.01'));
for(const bad of ['1.234','1e3','Infinity','1,000','--1','01.00'])check(()=>assert.throws(()=>parseCents(bad)));
check(()=>assert.deepEqual(occurrences({date:'2024-01-31',repeat:'monthly'},'2024-01-01','2024-04-30'),['2024-01-31','2024-02-29','2024-03-31','2024-04-30']));
check(()=>assert.deepEqual(occurrences({date:'2026-10-01',repeat:'weekly'},'2026-10-10','2026-10-22'),['2026-10-15','2026-10-22']));
const events=[{id:'pay',label:'Paycheck',date:'2026-10-15',repeat:'once',cents:10000},{id:'rent',label:'Rent',date:'2026-10-16',repeat:'once',cents:-18000}];
const config={start:'2026-10-14',end:'2026-10-17',openingCents:10000,events};
const base=project(config),scenario=project({...config,shiftId:'rent',shiftDays:1});
check(()=>assert.deepEqual(base.days.map(x=>x.balanceCents),[10000,20000,2000,2000]));
check(()=>assert.deepEqual(scenario.days.map(x=>x.balanceCents),[10000,20000,20000,2000]));
check(()=>assert.equal(base.minimumCents,2000));
check(()=>assert.equal(base.minimumDate,'2026-10-16'));
check(()=>assert.equal(config.events[1].date,'2026-10-16'));
check(()=>assert.throws(()=>project({...config,events:[events[0],events[0]]}),/unique/));
check(()=>assert.throws(()=>project({...config,end:'2028-01-01'}),/366/));
check(()=>assert.throws(()=>project({...config,shiftId:'missing',shiftDays:1}),/not found/));
// A nonzero shift with no selected event must never be silently presented as a scenario.
check(()=>assert.throws(()=>project({...config,shiftId:null,shiftDays:5}),/Choose an event to shift/));
check(()=>assert.throws(()=>project({...config,shiftId:null,shiftDays:-5}),/Choose an event to shift/));
check(()=>assert.throws(()=>project({...config,shiftId:null,shiftDays:NaN}),/whole number/));
check(()=>assert.throws(()=>project({...config,shiftId:null,shiftDays:61}),/between -60 and 60/));
check(()=>assert.deepEqual(project({...config,shiftId:null,shiftDays:0}).days,base.days));
check(()=>assert.ok(csvCell('=HYPERLINK(\"evil\")').includes("'=HYPERLINK")));
check(()=>assert.ok(csvCell('\t+SUM(1)').includes("'\t+SUM")));
check(()=>assert.ok(exportCSV(project({...config,events:[{...events[0],label:'=FORMULA'}]})).includes("'=FORMULA")));
check(()=>assert.ok(exportCSV(base).includes(',-180.00,20.00,')));
check(()=>assert.ok(!exportCSV(base).includes("'-180.00")));
check(()=>assert.deepEqual(occurrences({date:'2100-12-31',repeat:'monthly'},'2100-12-01','2100-12-31'),['2100-12-31']));
check(()=>assert.deepEqual(occurrences({date:'1900-01-31',repeat:'monthly'},'2100-12-01','2100-12-31'),['2100-12-31']));

// A CSV cell may be quoted today but later resaved with altered escaping.
// Reject separator/quote-adjacent formulas and any tab; preserve exact JSON.
const riskInputs=['safe,=1+1','safe;=1+1','safe"=1+1',"safe'=1+1",'safe\t=1+1','safe, \u200D＝SUM(1)'];
for(const label of riskInputs){
  const result=project({...config,events:[{...events[0],label}]});
  check(()=>assert.equal(csvExportRisk(result)?.field,'label'));
  check(()=>assert.throws(()=>exportSafeCSV(result),/CSV export blocked/));
  check(()=>assert.equal(JSON.parse(exportJSON(result)).days[1].events[0].label,label));
}
for(const label of ['Budget, October','Rent - November','Paycheck + tips']){
  const result=project({...config,events:[{...events[0],label}]});
  check(()=>assert.equal(csvExportRisk(result),null));
  check(()=>assert.ok(exportSafeCSV(result).includes(label)));
}
console.log(`${n} FT-04 deterministic assertions PASS`);
