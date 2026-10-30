'use strict';
const assert=require('node:assert/strict');
const {summarize,inspectSourceRecords,findSourceRecordOffset,withoutExactDuplicates,exportEvidenceJson,parseDelimited}=require('../rescue-core.js');
let checks=0;
function eq(a,b,label){assert.deepStrictEqual(a,b,label);checks++}
function fails(f,label){assert.throws(f,/source-record/i,label);checks++}
function table(rows,extra={}){return {headers:['ID','Value'],normalizedHeaders:['ID','Value'],warnings:[],delimiter:',',rows,...extra}}
const mapped=table([['A','one'],['A','one'],['B','two']],{originalRowCount:8,sourceRecords:[2,5,9]});
const before=JSON.stringify(mapped);
eq(summarize(mapped).duplicateRows,[{row:5,firstSeen:2}],'summary source IDs');
eq(inspectSourceRecords(mapped,'duplicates').entries,[{sourceRecord:5,duplicateOf:2,values:['A','one']}],'preview source IDs');
eq(findSourceRecordOffset(mapped,'duplicates',5),0,'lookup original ID');
eq(findSourceRecordOffset(mapped,'duplicates',3),null,'no fabricated ID');
eq(withoutExactDuplicates(mapped).sourceRecords,[2,9],'dedupe original IDs');
eq(JSON.stringify(mapped),before,'no mutation');
const filtered=table([['A','one'],['B','two']],{originalRowCount:8});
for(const [name,fn] of [['summary',()=>summarize(filtered)],['preview',()=>inspectSourceRecords(filtered)],['lookup',()=>findSourceRecordOffset(filtered,'all',2)],['dedupe',()=>withoutExactDuplicates(filtered)]])fails(fn,'filtered missing mapping '+name);
const malformed=[{sourceRecords:[2,2]},{sourceRecords:[5,4]},{sourceRecords:[2]},{sourceRecords:[2,50002]},{sourceRecords:['2',4]},{sourceRecords:null},{sourceRecords:[2,6],originalRowCount:3},{originalRowCount:-1},{originalRowCount:50001}];
for(const [i,extra] of malformed.entries()){const t=table([['A','one'],['B','two']],extra);for(const [name,fn] of [['summary',()=>summarize(t)],['preview',()=>inspectSourceRecords(t)],['lookup',()=>findSourceRecordOffset(t,'all',2)],['dedupe',()=>withoutExactDuplicates(t)]])fails(fn,'malformed '+i+' '+name)}
const unknown=withoutExactDuplicates(table([['A','one'],['B','two']],{sourceRecords:[2,8]}));
eq(unknown.originalRowCount,undefined,'unknown original count remains unknown');
eq(JSON.parse(exportEvidenceJson(unknown)).records.map(r=>r.sourceRecord),[2,8],'evidence retains mapped IDs');
const ordinary=parseDelimited('ID,Value\r\nA,one\r\nA,one\r\nB,two\r\n');
eq(summarize(ordinary).duplicateRows,[{row:3,firstSeen:2}],'unfiltered compatibility');
eq(inspectSourceRecords(ordinary,'duplicates').entries[0].sourceRecord,3,'unfiltered preview compatibility');
let seed=0x54f15a19;function next(){seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed}
for(let i=0;i<1000;i++){const a=2+(next()%20000),b=a+1+(next()%50),t=table([['K'+i,'x'],['K'+i,'x']],{sourceRecords:[a,b],originalRowCount:b-1});eq(summarize(t).duplicateRows,[{row:b,firstSeen:a}],'oracle summary '+i);eq(inspectSourceRecords(t,'duplicates').entries[0].sourceRecord,b,'oracle preview '+i);eq(findSourceRecordOffset(t,'duplicates',b),0,'oracle lookup '+i)}
console.log('FT-01 source-record preview integrity: '+checks+'/'+checks+' PASS');
