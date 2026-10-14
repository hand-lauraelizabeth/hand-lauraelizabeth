import assert from 'node:assert/strict';
import {serializeWorkspace,parseWorkspaceBytes,validateWorkspace,WORKSPACE_MAX_BYTES} from './workspace.mjs';
let n=0;function check(fn){fn();n++}
const config={start:'2026-10-14',end:'2026-11-14',opening:'125.25',shiftId:'rent-1',shiftDays:2};
const events=[{id:'rent-1',label:'Rent — October',date:'2026-10-15',repeat:'monthly',cents:-85000},{id:'pay',label:'Salary',date:'2026-10-16',repeat:'weekly',cents:105050}];
const data=JSON.parse(serializeWorkspace(config,events).json);
const bytes=new TextEncoder().encode(JSON.stringify(data));
check(()=>assert.equal(data.format,'ft04-cash-flow-workspace'));
check(()=>assert.equal(data.version,1));
check(()=>assert.deepEqual(parseWorkspaceBytes(bytes).events,events));
check(()=>assert.equal(parseWorkspaceBytes(new Uint8Array([0xef,0xbb,0xbf,...bytes])).events.length,2));
check(()=>assert.equal(validateWorkspace(data).settings.opening,'125.25'));
check(()=>assert.equal(data.events[0].id,'rent-1'));
check(()=>assert.equal(data.events[0].amount,'-850.00'));
check(()=>assert.equal(data.settings.shiftId,'rent-1'));
const mutated=(fn)=>{const copy=structuredClone(data);fn(copy);return new TextEncoder().encode(JSON.stringify(copy));};
const bad=[
 [d=>d.version=2,'version'],[d=>d.format='other','format'],
 [d=>d.events[0].id=d.events[1].id,'Duplicate'],
 [d=>d.events[0].amount='1e6','decimal'],
 [d=>d.events[0].date='2026-02-29','calendar'],
 [d=>d.events[0].repeat='daily','recurrence'],
 [d=>d.settings.shiftId='missing','not found'],
 [d=>d.settings.shiftDays=61,'Shift days'],
 [d=>d.settings.shiftDays='1','Shift days'],
 [d=>d.settings.start='2026-12-01','Choose 1'],
 [d=>d.settings.end='2028-01-01','366'],
 [d=>d.events[0].label='','description'],
 [d=>d.events[0].label='X'.repeat(121),'description'],
 [d=>d.events[0].id='\u0000bad','ID'],
 [d=>d.settings.unexpected='yes','unsupported'],
 [d=>d.events[0].unsafe=true,'unsupported'],
 [d=>d.events=new Array(201).fill(d.events[0]),'Too many'],
 [d=>d.events=null,'Too many'],
 [d=>d.events[0].amount='-10000000000.00','decimal'],
 [d=>d.settings.opening='NaN','decimal'],
];
for(const [fn,part] of bad)check(()=>assert.throws(()=>parseWorkspaceBytes(mutated(fn)),new RegExp(part,'i')));
check(()=>assert.throws(()=>parseWorkspaceBytes(new Uint8Array()),/1–1,000,000/));
check(()=>assert.throws(()=>parseWorkspaceBytes(new Uint8Array(WORKSPACE_MAX_BYTES+1)),/1–1,000,000/));
check(()=>assert.throws(()=>parseWorkspaceBytes(new Uint8Array([0xc3,0x28])),/UTF-8/));
check(()=>assert.throws(()=>parseWorkspaceBytes(new TextEncoder().encode('{oops')),/malformed JSON/));
check(()=>assert.throws(()=>parseWorkspaceBytes(new TextEncoder().encode('\u0000'+JSON.stringify(data))),/NUL/));
check(()=>assert.throws(()=>parseWorkspaceBytes(new TextEncoder().encode(JSON.stringify([data]))),/object/));
check(()=>assert.throws(()=>serializeWorkspace({...config,shiftId:'missing'},events),/not found/));
check(()=>assert.equal(serializeWorkspace(config,events).validated.events[0].label,'Rent — October'));
console.log(`${n} FT-04 workspace Node assertions PASS`);
