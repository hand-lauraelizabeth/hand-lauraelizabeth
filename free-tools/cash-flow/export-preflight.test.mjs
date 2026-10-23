import assert from 'node:assert/strict';
import {project,csvExportRisk,exportSafeCSV,exportJSON} from './engine.mjs';

// Synthetic-only differential export contract: unsafe spreadsheet-like text
// must not be downloadable as CSV, while exact identifiers survive in JSON.
const seed={start:'2026-10-14',end:'2026-10-15',openingCents:10000,events:[
 {id:'00017',label:'Rent - October',date:'2026-10-14',repeat:'once',cents:-1200}
]};
let checks=0;
function verify(value,message){assert.ok(value,message);checks++}
function projection(label,id='00017'){
 return project({...seed,events:[{...seed.events[0],id,label}]});
}
const safe=projection('Quoted "label", with\nsafe multiline');
verify(csvExportRisk(safe)===null,'benign punctuation and multiline permitted');
verify(exportSafeCSV(safe).includes('00017'),'leading-zero ID in safe CSV');
verify(exportSafeCSV(safe).includes('""label""'),'CSV quote escaping');
verify(exportSafeCSV(safe).includes('\r\n'),'CRLF row delimiter');
const safeJSON=JSON.parse(exportJSON(safe));
verify(safeJSON.schema==='cash-flow-scenario/v1','versioned JSON schema');
verify(safeJSON.days[0].events[0].id==='00017','lossless exact ID');
verify(safeJSON.days[0].events[0].label===seed.events[0].label.replace('Rent - October','Quoted "label", with\nsafe multiline'),'lossless multiline');
verify(safeJSON.days[0].balanceCents===8800,'integer-cents balance');

const unsafe=[
 '=1+1','+SUM(1,2)','-2+3','@SUM(1,2)',
 '＝1+1','＋SUM(1)','－1','＠SUM(1)',
 '\u200B=1+1','\u2060+1','\u200D@SUM(1)',
 '\uFE0F=1+1','\u202EVisible text',
 '\t=1+1','\r=1+1','\n=1+1',
 'Safe text\n=1+1','Safe text\r\n \u200B+SUM(1)'
];
for(const [i,label] of unsafe.entries()){
 for(const field of ['label','id']){
  const events=[{...seed.events[0],[field]:label}];
  const source=JSON.stringify(events);
  const result=project({...seed,events});
  const risk=csvExportRisk(result);
  verify(risk?.field===field,'risk '+i+' '+field);
  assert.throws(()=>exportSafeCSV(result),/CSV export blocked/);checks++;
  const lossless=JSON.parse(exportJSON(result));
  verify(lossless.days[0].events[0][field]===label,'JSON exact '+i+' '+field);
  verify(JSON.stringify(events)===source,'input unchanged '+i+' '+field);
 }
}
assert.throws(()=>exportSafeCSV({days:null}),/Invalid projection/);checks++;
assert.throws(()=>exportJSON({days:null}),/Invalid projection/);checks++;
console.log('PASS: '+checks+' FT-04 CSV fail-closed and lossless JSON assertions');
