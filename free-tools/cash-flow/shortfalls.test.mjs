import assert from 'node:assert/strict';
import {summarizeShortfalls} from './shortfalls.mjs';
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
console.log(checks+' FT-04 shortfall summary assertions PASS');
