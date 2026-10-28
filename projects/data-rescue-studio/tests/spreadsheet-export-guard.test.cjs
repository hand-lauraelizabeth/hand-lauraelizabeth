'use strict';
// Synthetic adversarial inputs only; no spreadsheet software or external data.
const assert=require('node:assert/strict');
const {parseDelimited,spreadsheetExportRisk,exportCsvDownload,exportEvidenceJson}=require('../rescue-core.js');
let count=0;
const eq=(a,b,msg)=>{assert.deepEqual(a,b,msg);count++};
const blocked=(input,row,col)=>{
 const parsed=parseDelimited(input);
 eq(spreadsheetExportRisk(parsed),{sourceRecord:row,column:col},'risk position');
 assert.throws(()=>exportCsvDownload(parsed,true),new RegExp('source record '+row+', column '+col));count++;
 eq(parseDelimited(exportCsvDownload(parsed,false)).rows,parsed.rows,'machine CSV exact roundtrip');
 eq(JSON.parse(exportEvidenceJson(parsed,'synthetic.csv')).records.map(x=>x.values),parsed.rows,'JSON exact source values');
};
blocked('ID,Note\\n01,"ordinary\\n=1+1"\\n'.replaceAll('\\n','\n'),2,2);
blocked('ID,Note\\n01,"ordinary\\r\\n   @SUM(1)"\\n'.replaceAll('\\r','\r').replaceAll('\\n','\n'),2,2);
blocked('ID,Note\\n01,"\\u202Edisguised"\\n'.replaceAll('\\n','\n').replace('\\u202E','\u202E'),2,2);
blocked('ID,Note\\n01,"\\u200B=1+1"\\n'.replaceAll('\\n','\n').replace('\\u200B','\u200B'),2,2);
blocked('ID,Note\\n01,"\\u0001hidden"\\n'.replaceAll('\\n','\n').replace('\\u0001','\u0001'),2,2);
blocked('=1+1,Note\\n01,ok\\n'.replaceAll('\\n','\n'),1,1); // Header is also untrusted.
const benign=parseDelimited('ID,Note\\n01,"ordinary\\r\\nmultiline"\\n'.replaceAll('\\r','\r').replaceAll('\\n','\n'));
eq(spreadsheetExportRisk(benign),null,'ordinary multiline accepted');
eq(parseDelimited(exportCsvDownload(benign,true)).rows,benign.rows,'benign spreadsheet CSV roundtrip');
const normalFormula=parseDelimited('ID,Note\\n01,=1+1\\n'.replaceAll('\\n','\n'));
eq(spreadsheetExportRisk(normalFormula),null,'known leading formula remains tab-prefixed in spreadsheet mode');
assert.ok(exportCsvDownload(normalFormula,true).includes('\\t=1+1'.replace('\\t','\t')));count++;
console.log('PASS: '+count+' spreadsheet export boundary, source position and exact JSON/CSV assertions.');
