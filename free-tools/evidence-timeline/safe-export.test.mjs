import assert from 'node:assert/strict';
import {csvExportRisk,exportSafeEvidenceCSV} from './safe-export.mjs';
let passed=0;
function check(name,fn){fn();passed++;console.log('PASS '+name)}
const base={sourceId:'00009',date:'2026-10-23',claim:'Invoice "A", paid; confirm',status:'reported',kind:'source',group:''};
check('safe evidence CSV retains zero-padded ID',()=>assert.match(exportSafeEvidenceCSV([base]),/"00009"/));
check('safe quoted punctuation remains one cell',()=>assert.match(exportSafeEvidenceCSV([base]),/"Invoice ""A"", paid; confirm"/));
check('safe export preserves exact whitespace',()=>assert.match(exportSafeEvidenceCSV([{...base,sourceId:' 00009 '}]),/" 00009 "/));
check('empty set yields only header',()=>assert.equal(exportSafeEvidenceCSV([]).trim(),'sourceId,date,claim,status,kind,group'));
for(const [label,value] of [
 ['equals','=1+1'],['plus','+SUM(A1)'],['minus','-1+2'],['at','@SUM(A1)'],
 ['fullwidth','＝1+1'],['fullwidth plus','＋1'],['fullwidth minus','－1'],['fullwidth at','＠1'],
 ['leading spaces','  =1+1'],['no-break space','\u00a0=1+1'],
 ['tab','\t=1+1'],['CR','\r=1+1'],['LF','\n=1+1'],
 ['NUL','x\u0000y'],['DEL','x\u007fy'],['bidi','abc\u202e123'],
 ['zero width','\u200b=1+1'],['word joiner','\u2060=1+1'],['BOM','\ufeff=1+1'],
 ['comma cell boundary','text,=1+1'],['semicolon boundary','text; =1+1'],
 ['Unicode separator','line\u2028=1+1'],['RTL isolate','x\u2067y']
]){
  for(const field of ['sourceId','claim','group']){
    const record={...base,[field]:value};
    check(label+' in '+field+' is fail-closed',()=>{
      assert.equal(csvExportRisk([record])?.field,field);
      assert.throws(()=>exportSafeEvidenceCSV([record]),/CSV export blocked/);
      assert.equal(record[field],value);
      assert.equal(JSON.parse(JSON.stringify({schema:'evidence-timeline-v1',records:[record]})).records[0][field],value);
    });
  }
}
check('no mutation of source record',()=>{const before=JSON.stringify(base);exportSafeEvidenceCSV([base]);assert.equal(JSON.stringify(base),before)});
check('non-string data fails closed',()=>assert.equal(csvExportRisk([{...base,claim:42}])?.field,'claim'));
check('invalid record fails closed',()=>assert.equal(csvExportRisk([null])?.field,'records'));
console.log('PASS '+passed+' FT-05 conservative CSV gate assertions');
