import assert from 'node:assert/strict';
import {exportEvidenceCSV} from './core.mjs';
const base={sourceId:'ID-1',date:'2026-10-14',claim:'ordinary',status:'reported',kind:'source',group:'group'};
let checks=0;
const check=(condition,label)=>{assert.ok(condition,label);checks++};
const quoted=value=>'"'+value.replaceAll('"','""')+'"';
for(const value of ['=1+1','+SUM(1,1)','-10+20','@SUM(A1:A2)','  =HYPERLINK("x","y")','\t=2+2','\r=3+3','\uFEFF=4+4']){
 const csv=exportEvidenceCSV([{...base,claim:value}]);
 check(csv.includes(quoted("'"+value)),'formula prefix escaped: '+JSON.stringify(value));
}
for(const value of ['ordinary','0','hello,world','"quoted"','multi\nline']){
 const csv=exportEvidenceCSV([{...base,claim:value}]);
 check(csv.includes(quoted(value)),'ordinary value preserved: '+JSON.stringify(value));
}
for(const column of ['sourceId','date','claim','status','kind','group']){
 const csv=exportEvidenceCSV([{...base,[column]:'=2+2'}]);
 check(csv.split('\r\n')[1].includes(quoted("'=2+2")),'column '+column+' escaped');
}
const id='  Exact "ID", with comma\nsecond line  ';
const csv=exportEvidenceCSV([{...base,sourceId:id}]);
check(csv.includes(quoted(id)),'exact source ID preserved and quoted');
check(exportEvidenceCSV([])==='sourceId,date,claim,status,kind,group\r\n','empty export header');
console.log(checks+' synthetic CSV security and provenance checks PASS');
