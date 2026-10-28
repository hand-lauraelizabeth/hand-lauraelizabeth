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
blocked('\\u200B=1+1,Note\\n01,ok\\n'.replaceAll('\\n','\n').replace('\\u200B','\u200B'),1,1); // Hidden-prefix header is also untrusted.
const benign=parseDelimited('ID,Note\\n01,"ordinary\\r\\nmultiline"\\n'.replaceAll('\\r','\r').replaceAll('\\n','\n'));
eq(spreadsheetExportRisk(benign),null,'ordinary multiline accepted');
eq(parseDelimited(exportCsvDownload(benign,true)).rows,benign.rows,'benign spreadsheet CSV roundtrip');
const normalFormula=parseDelimited('ID,Note\\n01,=1+1\\n'.replaceAll('\\n','\n'));
eq(spreadsheetExportRisk(normalFormula),null,'known leading formula remains tab-prefixed in spreadsheet mode');
assert.ok(exportCsvDownload(normalFormula,true).includes('\\t=1+1'.replace('\\t','\t')));count++;
// A duplicate before an unsafe cell must not renumber the source record.
const repeated=parseDelimited('ID,Note\n01,ok\n01,ok\n02,"safe\n=1+1"\n02,"safe\n=1+1"\n03,done\n');
const deduped=require('../rescue-core.js').withoutExactDuplicates(repeated);
eq(deduped.rows.length,3,'deduplication retains three distinct records');
eq(deduped.sourceRecords,[2,4,6],'original logical positions survive deduplication');
eq(deduped.originalRowCount,5,'original row count retained');
eq(spreadsheetExportRisk(deduped),{sourceRecord:4,column:2},'blocked export cites original record 4, not filtered record 3');
assert.throws(()=>exportCsvDownload(deduped,true),/source record 4, column 2/);count++;
eq(parseDelimited(exportCsvDownload(deduped,false)).rows,deduped.rows,'filtered machine CSV retains exact values');
const dedupedEvidence=JSON.parse(exportEvidenceJson(deduped,'synthetic.csv'));
eq(dedupedEvidence.records.map(r=>r.sourceRecord),[2,4,6],'filtered JSON retains original source positions');
eq(dedupedEvidence.source.originalDataRecords,5,'filtered JSON discloses original record count');
eq(dedupedEvidence.recordCount,3,'filtered JSON discloses retained count');
eq(require('../rescue-core.js').withoutExactDuplicates(deduped).sourceRecords,[2,4,6],'repeat dedupe does not renumber');
assert.throws(()=>exportEvidenceJson({...deduped,sourceRecords:[2,2,6]},'synthetic.csv'),/Invalid source-record positions/);count++;
assert.throws(()=>exportEvidenceJson({...deduped,originalRowCount:3},'synthetic.csv'),/Invalid original record count/);count++;
// Source headers may collide with generated labels. A reconciliation key must
// identify exactly one column, while raw CSV headers and evidence stay intact.
const {reconcile}=require('../reconcile-core.js');
const headerCases=[
  ['ID,ID,ID (2)\nX,A,ALPHA\nY,B,BETA\n',['ID','ID (2)','ID (2) (2)']],
  ['ID,ID (2),ID\nX,ALPHA,A\n',['ID','ID (2)','ID (3)']],
  ['id,ID,Id\nX,A,ALPHA\n',['id','ID (2)','Id (3)']],
  [',Column 1,Column 1 (2)\nX,A,ALPHA\n',['Column 1','Column 1 (2)','Column 1 (2) (2)']]
];
for(const [csv,labels] of headerCases){
  const table=parseDelimited(csv);
  eq(table.normalizedHeaders,labels,'distinct deterministic column choices');
  eq(new Set(labels.map(x=>x.toLowerCase())).size,labels.length,'case-insensitive choice uniqueness');
  eq(JSON.parse(exportEvidenceJson(table,'synthetic.csv')).headers,table.headers,'raw header fidelity');
  eq(parseDelimited(exportCsvDownload(table,false)).headers,table.headers,'machine CSV raw header roundtrip');
}
const collision=parseDelimited('ID,ID,ID (2)\nX,A,ALPHA\nY,B,BETA\n');
const target=parseDelimited('Join\nALPHA\nBETA\n');
eq(reconcile(collision,target,'ID (2) (2)','Join').matches.length,2,'third original column is selectable for reconciliation');
eq(reconcile(collision,target,'ID (2)','Join').matches.length,0,'second column remains independently selectable');
eq(collision.warnings.some(x=>x.includes('Column 3 was labeled')),true,'display-label collision is explained');
console.log('PASS: '+count+' spreadsheet export boundary, source position and exact JSON/CSV assertions.');
