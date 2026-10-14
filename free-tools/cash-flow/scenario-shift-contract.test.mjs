import assert from 'node:assert/strict';
import {project} from './engine.mjs';
const rent={id:'rent',label:'Rent',date:'2024-01-31',repeat:'monthly',cents:-2000};
const result=project({start:'2024-02-01',end:'2024-05-10',openingCents:10000,events:[rent],shiftId:'rent',shiftDays:1});
const actual=result.days.filter(day=>day.events.length).map(day=>day.date);
assert.deepEqual(actual,['2024-02-01','2024-03-01','2024-04-01','2024-05-01']);
console.log('Monthly occurrence-preserving shift contract PASS');
