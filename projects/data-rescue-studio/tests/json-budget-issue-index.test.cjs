'use strict';
// Synthetic-only FT-01 evidence-size and value-free issue-index regression.
const assert=require('node:assert/strict');
const {exportEvidenceJson,exportIssueIndexJson,requireJsonBudget,MAX_EVIDENCE_BYTES}=require('../rescue-core.js');
let checks=0;
function eq(a,b,label){assert.deepStrictEqual(a,b,label);checks++;}
function ok(a,label){assert.ok(a,label);checks++;}
function blocked(fn,label){assert.throws(fn,/JSON exceeds the 32 MB output limit/,label);checks++;}
function table(rows){return {headers:['ID','Value'],normalizedHeaders:['ID','Value'],warnings:[],delimiter:',',rows};}
const sample={...table([['0007','=2+2'],['0007','=2+2'],['0008',''],['é😀','line\nfeed']]),
 sourceRecords:[2,4,6,9],originalRowCount:8};
const sourceName='synthetic_sensitive_filename.csv';
const provenance={byteCount:91,sha256:'a'.repeat(64)};
const evidence=JSON.parse(exportEvidenceJson(sample,sourceName,provenance));
eq(evidence.records.map(r=>r.sourceRecord),[2,4,6,9],'original logical positions');
eq(evidence.records.map(r=>r.values),sample.rows,'exact Unicode/formula/blank cells');
eq(evidence.source.fileName,sourceName,'full evidence retains explicit filename');
eq(evidence.source.sha256,provenance.sha256,'full evidence retains validated digest');
const minimal=JSON.parse(exportIssueIndexJson(sample,sourceName,provenance));
eq(minimal.issues,[{sourceRecord:4,blankColumns:[],duplicateOf:2},
 {sourceRecord:6,blankColumns:[2],duplicateOf:null}],'value-free findings and exact duplicate link');
eq(minimal.counts,{recordsWithBlankCells:1,repeatedExactRecords:1,issueRecords:2},'issue counts');
ok(!Object.hasOwn(minimal.source,'fileName')&&!Object.hasOwn(minimal.source,'sha256'),'metadata omitted by default');
ok(!JSON.stringify(minimal).includes('0007')&&!JSON.stringify(minimal).includes('=2+2'),'values excluded');
const opted=JSON.parse(exportIssueIndexJson(sample,sourceName,provenance,true));
eq(opted.source.fileName,sourceName,'explicit filename opt-in');
eq(opted.source.sha256,provenance.sha256,'explicit digest opt-in');
eq(opted.issues,minimal.issues,'opt-in does not alter findings');
const oldStringify=JSON.stringify;
let fullEvidenceAttempted=false;
try{
 JSON.stringify=(value,...rest)=>{
  if(value && value.format==='data-rescue-evidence'){fullEvidenceAttempted=true;throw Error('full-value serialization forbidden');}
  return oldStringify(value,...rest);
 };
 eq(JSON.parse(exportIssueIndexJson(sample,sourceName,provenance)).issues,minimal.issues,
  'issue index works without full evidence serialization');
}finally{JSON.stringify=oldStringify;}
eq(fullEvidenceAttempted,false,'issue index never builds full-value evidence JSON');
eq(MAX_EVIDENCE_BYTES,32_000_000,'explicit JSON byte cap');
// FT-03 comparison JSON shares the exact byte budget, including UTF-8 and escaping.
eq(requireJsonBudget('x'.repeat(MAX_EVIDENCE_BYTES),'Comparison audit').length,MAX_EVIDENCE_BYTES,
 'comparison exact byte boundary accepted');
blocked(()=>requireJsonBudget('x'.repeat(MAX_EVIDENCE_BYTES+1),'Comparison audit'),
 'comparison ASCII over limit rejected');
blocked(()=>requireJsonBudget('é'.repeat(16_000_001),'Comparison audit'),
 'comparison UTF-8 byte limit enforced');
blocked(()=>requireJsonBudget('\\"'.repeat(16_000_001),'Comparison audit'),
 'comparison escaped JSON expansion enforced');
eq(requireJsonBudget('{"id":"😀","key":"=1+1"}','Comparison audit'),
 '{"id":"😀","key":"=1+1"}','comparison exact Unicode and formula-like keys unchanged');
eq(requireJsonBudget('{"empty":""}','Comparison audit'),'{"empty":""}',
 'comparison empty identifier preserved');
const empty={...table([['','']])};
const baselineBytes=Buffer.byteLength(exportEvidenceJson(empty),'utf8');
const atLimit={...table([['x'.repeat(MAX_EVIDENCE_BYTES-baselineBytes),'']])};
eq(Buffer.byteLength(exportEvidenceJson(atLimit),'utf8'),MAX_EVIDENCE_BYTES,'exact UTF-8 boundary accepted');
const over={...table([['x'.repeat(MAX_EVIDENCE_BYTES-baselineBytes+1),'']])};
blocked(()=>exportEvidenceJson(over),'one ASCII byte over limit rejected');
const oversized={...table([['x'.repeat(MAX_EVIDENCE_BYTES+100),'']])};
blocked(()=>exportEvidenceJson(oversized),'preflight rejects huge input without full JSON');
eq(JSON.parse(exportIssueIndexJson(oversized)).recordCount,1,
 'small issue index remains available when full evidence exceeds limit');
blocked(()=>exportEvidenceJson(table([['é'.repeat(16_100_000),'']])),
 'UTF-8 multibyte limit, not UTF-16 length');
blocked(()=>exportEvidenceJson(table([['"'.repeat(16_100_000),'']])),
 'JSON escape expansion counted');
for(const bad of [
 {...sample,sourceRecords:[2,4,4,9]},
 {...sample,sourceRecords:[2,4,6,10]},
 {...sample,originalRowCount:2},
 {...sample,rows:[['0007']]},
]) {
 assert.throws(()=>exportIssueIndexJson(bad),/source-record|original record|incomplete|inconsistent/i);
 checks++;
}
console.log('FT-01 bounded evidence/value-free index: '+checks+'/'+checks+' PASS');
