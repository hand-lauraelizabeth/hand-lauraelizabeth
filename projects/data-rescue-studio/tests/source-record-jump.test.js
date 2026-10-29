'use strict';
const assert=require('node:assert/strict');
const lib=require('../rescue-core.js');
let checks=0;
const eq=(actual,expected,label)=>{assert.deepEqual(actual,expected,label);checks++;};
const fail=(fn,label)=>{assert.throws(fn,/valid original source-record/,label);checks++;};
const parsed=lib.parseDelimited('id,note\\n1,alpha\\n2,\\n1,alpha\\n3,done\\n4,\\n1,alpha',',');
for(const [mode,record,expected] of [
 ['all',2,0],['all',7,5],['all',100,null],
 ['missing',3,0],['missing',6,1],['missing',2,null],
 ['duplicates',4,0],['duplicates',7,1],['duplicates',2,null]
])eq(lib.findSourceRecordOffset(parsed,mode,record),expected,mode+' record '+record);
for(const invalid of [0,1,1.5,50002,NaN,Infinity,'2'])fail(()=>lib.findSourceRecordOffset(parsed,'all',invalid),'invalid target '+invalid);
fail(()=>lib.findSourceRecordOffset(parsed,'unknown',2),'invalid filter');
const retained=lib.withoutExactDuplicates(parsed);
eq(lib.findSourceRecordOffset(retained,'all',6),3,'original source position retained after deduplication');
eq(lib.findSourceRecordOffset(retained,'all',7),null,'removed source record cannot be jumped to');
const original=JSON.stringify(parsed);
lib.findSourceRecordOffset(parsed,'duplicates',7);
eq(JSON.stringify(parsed),original,'navigation does not modify source');
const large=lib.parseDelimited('ID\\n'+Array.from({length:50000},(_,i)=>String(i)).join('\\n'),',');
eq(lib.findSourceRecordOffset(large,'all',50001),49999,'50,000th row reachable by source ID');
eq(lib.inspectSourceRecords(large,'all',20,49980).entries.at(-1).sourceRecord,50001,'last page retains original ID');
console.log('PASS: '+checks+' original-record direct-navigation assertions.');
