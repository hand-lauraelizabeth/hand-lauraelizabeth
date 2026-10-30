'use strict';
// Synthetic-only source-record provenance in spreadsheet export warnings.
const assert = require('node:assert/strict');
const {spreadsheetExportRisk, exportCsv, exportCsvDownload} = require('../rescue-core.js');
let checks=0;
function eq(a,b,label){assert.deepStrictEqual(a,b,label);checks++}
function fails(fn,label){assert.throws(fn,/source-record/i,label);checks++}
function table(rows,extra={}) {
 return {headers:['ID'],normalizedHeaders:['ID'],rows,warnings:[],delimiter:',',...extra};
}
// Negative control: the old warning incorrectly identified source record 2.
const missing=table([['\u2028']],{originalRowCount:5});
for(const [name,fn] of [
 ['risk',()=>spreadsheetExportRisk(missing)],
 ['csv',()=>exportCsv(missing,true)],
 ['download',()=>exportCsvDownload(missing,true)]])fails(fn,'missing original IDs '+name);
const outOfRange=table([['\u2028']],{sourceRecords:[99],originalRowCount:5});
const repeated=table([['A'],['\u2028']],{sourceRecords:[2,2],originalRowCount:5});
for(const input of [outOfRange,repeated]) {
 fails(()=>spreadsheetExportRisk(input),'invalid mapped source IDs');
 fails(()=>exportCsv(input,true),'invalid mapped CSV export');
 fails(()=>exportCsvDownload(input,true),'invalid mapped CSV download');
}
const mapped=table([['\u2028']],{sourceRecords:[6],originalRowCount:5});
eq(spreadsheetExportRisk(mapped),{sourceRecord:6,column:1},'exact warning position');
assert.throws(()=>exportCsv(mapped,true),/source record 6, column 1/);checks++;
eq(spreadsheetExportRisk(table([['safe']])),null,'ordinary input accepted');
eq(exportCsv(table([['safe']]),true),'"ID"\r\n"safe"','ordinary CSV preserved');
// Machine-readable CSV has no source-record claims; it is not spreadsheet-safe.
eq(exportCsv(missing,false),'"ID"\r\n"\u2028"','exact machine CSV remains distinct');
for(let i=0;i<2000;i++){
 const record=3+i%300, valid=table([['\u2028']],{sourceRecords:[record],originalRowCount:record-1});
 eq(spreadsheetExportRisk(valid),{sourceRecord:record,column:1},'original warning '+i);
}
console.log('FT-01 spreadsheet warning provenance: '+checks+'/'+checks+' PASS');
