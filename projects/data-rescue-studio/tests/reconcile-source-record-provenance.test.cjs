'use strict';
// Synthetic-only FT-01/FT-03 source-position regression.
// A filtered or deduplicated table must never be silently renumbered.
const assert=require('node:assert/strict');
const {reconcile}=require('../reconcile-core.js');
const {parseDelimited,withoutExactDuplicates}=require('../rescue-core.js');
let checks=0;
function same(actual,expected,label){assert.deepStrictEqual(actual,expected,label);checks++;}
function rejects(left,right,label){
 assert.throws(()=>reconcile(left,right,'ID','ID'),/Invalid original source-record|Invalid reconciliation identifier/,label);checks++;
}
const left={normalizedHeaders:['ID'],rows:[['A'],[''],['A'],['B'],['L']],
 sourceRecords:[2,5,8,11,15],originalRowCount:20};
const right={normalizedHeaders:['ID'],rows:[['A'],['B'],[''],['R']],
 sourceRecords:[3,7,10,19],originalRowCount:20};
const leftBefore=JSON.stringify(left),rightBefore=JSON.stringify(right);
const result=reconcile(left,right,'ID','ID');
same(result.ambiguous,[{key:'A',leftRows:[2,8],rightRows:[3]}],'ambiguous keys retain every original position');
same(result.matches,[{key:'B',leftRow:11,rightRow:7}],'unique matches retain original positions');
same(result.leftOnly,[{key:'L',row:15}],'left-only position retained');
same(result.rightOnly,[{key:'R',row:19}],'right-only position retained');
same(result.missingLeft,[5],'missing left identifier retains original position');
same(result.missingRight,[10],'missing right identifier retains original position');
same(JSON.stringify(left),leftBefore,'left source unchanged');
same(JSON.stringify(right),rightBefore,'right source unchanged');
// Baseline reproduction: the previous sequential-row implementation would have
// reported left row 5 and right row 3 as 3 and 2, respectively.
assert.notDeepStrictEqual(result.matches,[{key:'B',leftRow:5,rightRow:3}]);checks++;
const rawLeft=parseDelimited('ID,Value\r\nA,one\r\nA,one\r\nB,two\r\n');
const rawRight=parseDelimited('ID,Value\r\nA,one\r\nB,two\r\n');
const deduped=withoutExactDuplicates(rawLeft);
same(deduped.sourceRecords,[2,4],'deduplication produces noncontiguous original IDs');
same(reconcile(deduped,rawRight,'ID','ID').matches,
 [{key:'A',leftRow:2,rightRow:2},{key:'B',leftRow:4,rightRow:3}],
 'real parser plus deduplication retains original logical CSV records');
same(reconcile(rawLeft,rawRight,'ID','ID').ambiguous,
 [{key:'A',leftRows:[2,3],rightRows:[2]}],
 'ordinary raw inputs still use sequential logical record positions');
// Strictly increasing, bounded, aligned positions are mandatory when supplied.
for(const bad of [[2,2],[5,4],[1,4],[2,50002],[2,'4'],[2],[2,Number.MAX_SAFE_INTEGER],null,'2,4']){
 rejects({normalizedHeaders:['ID'],rows:[['A'],['B']],sourceRecords:bad},rawRight,
 'reject malformed source-record list '+String(bad));
}
for(const originalRowCount of [-1,0,1,50001,2.5,'20']){
 rejects({normalizedHeaders:['ID'],rows:[['A'],['B']],sourceRecords:[2,4],originalRowCount},rawRight,
 'reject malformed original record count '+originalRowCount);
}
rejects({normalizedHeaders:['ID'],rows:[['A'],['B']],sourceRecords:[2,4],originalRowCount:2},
 rawRight,'reject source position beyond declared original record count');
rejects({normalizedHeaders:['ID'],rows:[['A'],[null]],sourceRecords:[2,4]},rawRight,
 'reject nonstring identifier');
// Deterministic synthetic oracle: both sides contain the same unique key,
// but each has a different original source position.
let state=0x5f3759df;
function next(){state=(Math.imul(state,1664525)+1013904223)>>>0;return state;}
for(let i=0;i<1000;i++){
 const a=2+(next()%20000),b=2+(next()%20000);
 const key='case-'+i;
 const x={normalizedHeaders:['ID'],rows:[[key]],sourceRecords:[a],originalRowCount:20001};
 const y={normalizedHeaders:['ID'],rows:[[key]],sourceRecords:[b],originalRowCount:20001};
 same(reconcile(x,y,'ID','ID').matches,[{key,leftRow:a,rightRow:b}],
  'seeded provenance scenario '+i);
}
// Negative control must be observably wrong: the old algorithm discarded
// explicit source positions and always reported sequential row 2.
const negativeControl={key:'probe',leftRow:2,rightRow:2};
const corrected=reconcile(
 {normalizedHeaders:['ID'],rows:[['probe']],sourceRecords:[9],originalRowCount:10},
 {normalizedHeaders:['ID'],rows:[['probe']],sourceRecords:[7],originalRowCount:10},
 'ID','ID').matches[0];
assert.notDeepStrictEqual(corrected,negativeControl,'negative control detects legacy renumbering');checks++;
same(corrected,{key:'probe',leftRow:9,rightRow:7},'positive control retains source IDs');
console.log('FT-01/03 original source-record reconciliation: '+checks+'/'+checks+' PASS');
