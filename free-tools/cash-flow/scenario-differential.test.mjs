// Deterministic, independent day-by-day oracle for browser-local cash-flow projections.
// Synthetic values only. No network access, accounts, or financial recommendations.
import assert from 'node:assert/strict';
import {project} from './engine.mjs';

const DAY=86400000;
const timestamp=s=>{const [y,m,d]=s.split('-').map(Number);return Date.UTC(y,m-1,d)};
const iso=t=>new Date(t).toISOString().slice(0,10);
function isDue(event,day){
  const t=timestamp(day),first=timestamp(event.date);
  if(t<first)return false;
  if(event.repeat==='once')return t===first;
  if(event.repeat==='weekly')return (t-first)%(7*DAY)===0;
  const [y,m,d]=day.split('-').map(Number);
  const [ay,am,ad]=event.date.split('-').map(Number);
  if(y*12+m<ay*12+am)return false;
  return d===Math.min(ad,new Date(Date.UTC(y,m,0)).getUTCDate());
}
function independentDailyOracle(config){
  const days=[];
  // Independent reference: compute closing balances first; the opening input is
  // not an observed daily close and must not bias the minimum.
  let balance=config.openingCents,minimum=null,minDate=null;
  for(let t=timestamp(config.start);t<=timestamp(config.end);t+=DAY){
    const date=iso(t),items=[];
    for(const event of config.events){
      const shift=event.id===config.shiftId?config.shiftDays:0;
      if(isDue(event,iso(t-shift*DAY))){
        items.push({id:event.id,label:event.label,cents:event.cents});
      }
    }
    const change=items.reduce((sum,event)=>sum+event.cents,0);
    balance+=change;
    if(minimum===null||balance<minimum){minimum=balance;minDate=date}
    days.push({date,changeCents:change,balanceCents:balance,events:items});
  }
  return {days,minimumCents:minimum,minimumDate:minDate,
    endingCents:balance,openingCents:config.openingCents};
}
let seed=0xC0FFEE12;
function random(){seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed}
function range(low,high){return low+(random()%(high-low+1))}
let checks=0;
function compare(config,caseName){
  const actual=project(config),expected=independentDailyOracle(config);
  assert.deepEqual(actual.days,expected.days,caseName+' daily amounts and exact IDs');checks++;
  assert.equal(actual.minimumCents,expected.minimumCents,caseName+' minimum');checks++;
  assert.equal(actual.minimumDate,expected.minimumDate,caseName+' minimum date');checks++;
  assert.equal(actual.endingCents,expected.endingCents,caseName+' ending balance');checks++;
  assert.equal(actual.openingCents,expected.openingCents,caseName+' opening balance');checks++;
  return {actual,expected};
}
for(let scenario=0;scenario<350;scenario++){
  const start=iso(timestamp('2024-01-01')+range(0,1150)*DAY);
  const end=iso(timestamp(start)+range(1,90)*DAY);
  const events=Array.from({length:range(1,5)},(_,i)=>({
    id:'evt-'+String(i).padStart(3,'0'),label:'Synthetic '+i,
    date:iso(timestamp(start)-range(0,90)*DAY),
    repeat:['once','weekly','monthly'][range(0,2)],
    cents:range(-25000,30000)
  }));
  const openingCents=range(-100000,100000);
  const shiftId=events[range(0,events.length-1)].id;
  const shiftDays=range(-12,12);
  const base={start,end,openingCents,events,shiftId:null,shiftDays:0};
  const before=JSON.stringify(events);
  compare(base,'baseline '+scenario);
  compare({...base,shiftId,shiftDays},'shifted '+scenario);
  assert.equal(JSON.stringify(events),before,'source events not mutated '+scenario);checks++;
}
// Explicit leap-day and month-end occurrence shifts are included independently of the seed.
const edge={start:'2024-01-29',end:'2024-04-05',openingCents:12345,
  events:[{id:'0007',label:'Synthetic January rent',date:'2024-01-31',repeat:'monthly',cents:-1550}],
  shiftId:'0007',shiftDays:1};
const edgeActual=compare(edge,'leap/month-end');
assert.deepEqual(edgeActual.actual.days.filter(d=>d.events.length).map(d=>d.date),
  ['2024-02-01','2024-03-01','2024-04-01'],'month-end shift preserves anchor');checks++;
const tampered=structuredClone(edgeActual.actual.days);
tampered[0].changeCents++;
assert.notDeepEqual(tampered,edgeActual.expected.days,'negative control detects altered output');checks++;
console.log('PASS: '+checks+' FT-04 independent baseline/shifted oracle assertions (350 synthetic scenarios + leap/month-end + negative control).');
