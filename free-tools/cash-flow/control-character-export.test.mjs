import assert from 'node:assert/strict';
import {project,csvExportRisk,exportSafeCSV,exportJSON} from './engine.mjs';

// Synthetic-only adversarial import/export boundaries; no user files.
const base={start:'2026-10-23',end:'2026-10-23',openingCents:12500};
const values=[
  '\u0000=1+1','prefix\u0000=1+1','\u0001+1','\u0008@SUM(1)',
  '\u000B=1+1','\u000C=1+1','\u001F=1+1',
  '\u007F=1+1','\u0085=1+1','\u009F=1+1',
  '\u2028=1+1','\u2029=1+1','safe\u001Ftext'
];
let checks=0;
for(const value of values){
  for(const field of ['id','label']){
    const event={id:'00009',label:'Invoice',date:base.start,repeat:'once',cents:-1200};
    event[field]=value;
    const original=JSON.stringify(event);
    const result=project({...base,events:[event]});
    assert.equal(csvExportRisk(result)?.field,field);checks++;
    assert.throws(()=>exportSafeCSV(result),/CSV export blocked/);checks++;
    assert.equal(JSON.parse(exportJSON(result)).days[0].events[0][field],value);checks++;
    assert.equal(JSON.stringify(event),original);checks++;
  }
}
const benign=project({...base,events:[{id:'00009',label:'Invoice, with "quotes"\nand second line',date:base.start,repeat:'once',cents:-1200}]});
assert.equal(csvExportRisk(benign),null);checks++;
assert.match(exportSafeCSV(benign),/"Invoice, with ""quotes""\nand second line"/);checks++;
assert.equal(JSON.parse(exportJSON(benign)).days[0].events[0].id,'00009');checks++;
assert.equal(benign.endingCents,11300);checks++;
console.log('PASS: '+checks+' FT-04 control-character export boundary assertions');
