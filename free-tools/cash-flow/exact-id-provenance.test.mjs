import assert from 'node:assert/strict';
import {project,csvExportRisk,exportSafeCSV,exportJSON} from './engine.mjs';

// Synthetic source identifiers only. No financial records or uploaded files.
const config={start:'2026-10-23',end:'2026-10-25',openingCents:10000};
const event={id:' 00009 ',label:' Invoice  ',date:'2026-10-23',repeat:'once',cents:-1200};
let passed=0;
function check(name,fn){fn();passed++;console.log('PASS '+name)}
const original=JSON.stringify(event);
const baseline=project({...config,events:[event]});
const shifted=project({...config,events:[event],shiftId:event.id,shiftDays:1});
check('baseline retains source ID',()=>assert.equal(baseline.days[0].events[0].id,event.id));
check('baseline retains label spaces',()=>assert.equal(baseline.days[0].events[0].label,event.label));
check('shift moves occurrence without changing source ID',()=>{
  assert.equal(shifted.days[0].events.length,0);
  assert.equal(shifted.days[1].events[0].id,event.id);
  assert.equal(shifted.days[1].events[0].label,event.label);
  assert.equal(shifted.days[1].changeCents,-1200);
});
check('shift leaves expected ending balance',()=>assert.equal(shifted.endingCents,8800));
check('safe CSV accepts benign whitespace',()=>assert.equal(csvExportRisk(shifted),null));
check('CSV preserves original source fields',()=>assert.match(exportSafeCSV(shifted),/" 00009 "," Invoice  "/));
check('JSON preserves exact source fields and shifted day',()=>{
  const obj=JSON.parse(exportJSON(shifted));
  assert.equal(obj.days[1].date,'2026-10-24');
  assert.equal(obj.days[1].events[0].id,event.id);
  assert.equal(obj.days[1].events[0].label,event.label);
});
check('projection does not mutate source event',()=>assert.equal(JSON.stringify(event),original));
const distinct={...event,id:'00009',label:'Other',cents:-100};
const together=project({...config,events:[event,distinct],shiftId:event.id,shiftDays:1});
check('exact padded and unpadded IDs remain distinct',()=>{
  assert.equal(together.days[0].events[0].id,'00009');
  assert.equal(together.days[1].events[0].id,' 00009 ');
});
for(const id of ['', '   ', '\t', '\u2003']){
  check('whitespace-only ID rejected '+JSON.stringify(id),()=>assert.throws(
    ()=>project({...config,events:[{...event,id}]}),/IDs must be unique and nonempty/
  ));
}
for(const label of ['', '  ', '\t']){
  check('whitespace-only label rejected '+JSON.stringify(label),()=>assert.throws(
    ()=>project({...config,events:[{...event,label}]}),/Invalid event label/
  ));
}
for(const [field,value] of [['id',' =1+1'],['label','\u200B=1+1']]){
  const suspect={...event,[field]:value};
  const projection=project({...config,events:[suspect]});
  check('leading invisible/formula prefix blocks CSV '+field,()=>{
    assert.equal(csvExportRisk(projection)?.field,field);
    assert.throws(()=>exportSafeCSV(projection),/CSV export blocked/);
    assert.equal(JSON.parse(exportJSON(projection)).days[0].events[0][field],value);
  });
}
console.log('PASS '+passed+' FT-04 independent exact-ID provenance assertions');
