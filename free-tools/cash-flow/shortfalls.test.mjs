import assert from 'node:assert/strict';
import {summarizeShortfalls,compareBelowZeroDates} from './shortfalls.mjs';
let checks=0;
const check=(actual,expected)=>{assert.deepEqual(actual,expected);checks++;};
const projection=(balances,start='2026-10-01')=>({days:balances.map((balanceCents,i)=>({date:new Date(Date.parse(start+'T00:00:00Z')+i*86400000).toISOString().slice(0,10),balanceCents}))});
const empty={daysBelowZero:0,firstBelowZeroDate:null,lowestBalanceCents:null,longestRunDays:0,periods:[]};
check(summarizeShortfalls(projection([0,0,100])),empty);
check(summarizeShortfalls(projection([-1])),{daysBelowZero:1,firstBelowZeroDate:'2026-10-01',lowestBalanceCents:-1,longestRunDays:1,periods:[{start:'2026-10-01',end:'2026-10-01',days:1}]});
check(summarizeShortfalls(projection([-200,-100,0,-500,-300,0,-1])),{daysBelowZero:5,firstBelowZeroDate:'2026-10-01',lowestBalanceCents:-500,longestRunDays:2,periods:[{start:'2026-10-01',end:'2026-10-02',days:2},{start:'2026-10-04',end:'2026-10-05',days:2},{start:'2026-10-07',end:'2026-10-07',days:1}]});
const input=projection([-1,0,-2]);const before=JSON.stringify(input);
summarizeShortfalls(input);check(JSON.stringify(input),before);
for(const bad of [null,{}, {days:[]}, {days:Array(367).fill({date:'2026-10-01',balanceCents:0})},
 {days:[{date:'2026-02-30',balanceCents:-1}]},
 {days:[{date:'2026-10-01',balanceCents:0},{date:'2026-10-03',balanceCents:-1}]},
 {days:[{date:'2026-10-01',balanceCents:NaN}]},
 {days:[{date:'2026-10-01',balanceCents:1.5}]},
 {days:[{date:'2026-10-01',balanceCents:-1_000_000_000_001}]}]){
 assert.throws(()=>summarizeShortfalls(bad));checks++;
}
// Independent naive oracle for the count, first date, minimum and longest run.
let seed=0x5a17c0de;const random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296);
for(let sample=0;sample<600;sample++){
 const balances=Array.from({length:1+Math.floor(random()*366)},()=>Math.floor(random()*9-4)*100);
 const got=summarizeShortfalls(projection(balances,'2024-01-01'));
 const below=balances.map((n,i)=>n<0?i:-1).filter(i=>i>=0);
 let run=0,longest=0;for(const n of balances){run=n<0?run+1:0;longest=Math.max(longest,run);}
 assert.equal(got.daysBelowZero,below.length);
 assert.equal(got.firstBelowZeroDate,below.length?projection(balances,'2024-01-01').days[below[0]].date:null);
 assert.equal(got.lowestBalanceCents,below.length?Math.min(...balances.filter(n=>n<0)):null);
 assert.equal(got.longestRunDays,longest);
 assert.equal(got.periods.reduce((n,p)=>n+p.days,0),below.length);
 checks+=5;
}

// Exact four-way partition: the comparison is by matching calendar date,
// not by order of shortfall periods or by the minimum alone.
check(compareBelowZeroDates(projection([-1,0,-2,-3,0]),projection([0,-1,-2,0,0])),{
  noLongerBelowZero:2,newlyBelowZero:1,stillBelowZero:1,nonnegativeInBoth:1,
  firstNoLongerBelowZeroDate:'2026-10-01',firstNewlyBelowZeroDate:'2026-10-02'
});
check(compareBelowZeroDates(projection([0,0]),projection([0,0])),{
  noLongerBelowZero:0,newlyBelowZero:0,stillBelowZero:0,nonnegativeInBoth:2,
  firstNoLongerBelowZeroDate:null,firstNewlyBelowZeroDate:null
});
for(const [a,b] of [[projection([0]),projection([0,0])],
 [projection([0]),projection([0],'2026-10-02')],
 [projection([0,0]),projection([0,0],'2026-10-02')]]){
 assert.throws(()=>compareBelowZeroDates(a,b),/same projected dates/);checks++;
}
assert.throws(()=>compareBelowZeroDates(projection([0]),{days:[{date:'2026-10-01',balanceCents:NaN}]}));checks++;
// Independently compute transitions directly from raw synthetic cent arrays.
let comparisonSeed=0x4e34a1f0;
const next=()=>((comparisonSeed=(Math.imul(comparisonSeed,1664525)+1013904223)>>>0)/4294967296);
for(let sample=0;sample<700;sample++){
 const n=1+Math.floor(next()*366),a=[],b=[];
 for(let i=0;i<n;i++){a.push(Math.floor(next()*7-3)*100);b.push(Math.floor(next()*7-3)*100);}
 const result=compareBelowZeroDates(projection(a,'2024-01-01'),projection(b,'2024-01-01'));
 const states=a.map((v,i)=>Number(v<0)*2+Number(b[i]<0));
 const count=state=>states.filter(x=>x===state).length;
 assert.equal(result.noLongerBelowZero,count(2));
 assert.equal(result.newlyBelowZero,count(1));
 assert.equal(result.stillBelowZero,count(3));
 assert.equal(result.nonnegativeInBoth,count(0));
 assert.equal(Object.values(result).slice(0,4).reduce((x,y)=>x+y,0),n);
 const first=(state)=>{const index=states.indexOf(state);return index<0?null:projection(a,'2024-01-01').days[index].date};
 assert.equal(result.firstNoLongerBelowZeroDate,first(2));
 assert.equal(result.firstNewlyBelowZeroDate,first(1));
 checks+=7;
}

console.log(checks+' FT-04 shortfall summary assertions PASS');
