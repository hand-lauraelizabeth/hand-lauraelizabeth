import assert from 'node:assert/strict';
import {exportPlan,parsePlanJSON,readPlanFile,PLAN_SCHEMA,MAX_PLAN_BYTES} from './plan.mjs';
const seed={schema:PLAN_SCHEMA,start:'2026-10-25',end:'2026-11-25',openingCents:12345,
 events:[{id:' 00007 ',label:'\u03a9\n=1+1',date:'2026-10-31',repeat:'monthly',cents:-10025},
 {id:'pay',label:'Paycheck',date:'2026-10-26',repeat:'weekly',cents:40000}],
 shiftId:' 00007 ',shiftDays:2};
let n=0;const pending=[];function check(fn){const result=fn();if(result&&typeof result.then==='function')pending.push(result);n++;}
const json=exportPlan(seed),restored=parsePlanJSON(json);
check(()=>assert.deepEqual(restored,seed));
check(()=>assert.equal(restored.events[0].id,' 00007 '));
check(()=>assert.equal(restored.events[0].label,'\u03a9\n=1+1'));
check(()=>assert.equal(restored.events[0].cents,-10025));
check(()=>assert.equal(restored.shiftId,' 00007 '));
check(()=>assert.deepEqual(parsePlanJSON('\uFEFF'+json),seed));
check(()=>assert.equal(exportPlan(restored),json));
const bad=[
 {...seed,schema:'cash-flow-scenario/v1'}, {...seed,extra:'ignore-me'},
 {...seed,events:[seed.events[0],seed.events[0]]},
 {...seed,events:[{...seed.events[0],extra:'unexpected'}]},
 {...seed,events:[{...seed.events[0],id:'a'.repeat(51)}]},
 {...seed,events:[{...seed.events[0],label:' '}]},
 {...seed,events:[{...seed.events[0],cents:1.5}]},
 {...seed,events:[{...seed.events[0],repeat:'daily'}]},
 {...seed,events:[{...seed.events[0],date:'2026-02-30'}]},
 {...seed,events:Array(201).fill(0).map((_,i)=>({...seed.events[0],id:String(i)}))},
 {...seed,shiftId:'missing'}, {...seed,shiftDays:61},
 {...seed,shiftId:null,shiftDays:5}, {...seed,shiftId:null,shiftDays:-5},
 {...seed,openingCents:Infinity}, {...seed,openingCents:1.5},
 {...seed,start:'2026-12-01'}, {...seed,end:'2028-01-01'},
 {...seed,events:[{...seed.events[0],id:' '}]},
 {...seed,events:[{...seed.events[0],id:7}]},
 {...seed,events:[{...seed.events[0],label:null}]},
 {...seed,events:[{...seed.events[0],cents:1000000000001}]}
];
for(const [i,v] of bad.entries())check(()=>assert.throws(()=>parsePlanJSON(JSON.stringify(v)),undefined,'invalid case '+i));
for(const s of ['', '{', '[]','null','"string"','{"__proto__":{"polluted":true}}'])
 check(()=>assert.throws(()=>parsePlanJSON(s)));
// A shifted scenario can hide an overflowing *baseline* by moving a payment
// outside the selected window. Import and save must validate both projections.
const baselineOverflow={schema:PLAN_SCHEMA,start:'2026-10-25',end:'2026-10-25',
 openingCents:1000000000000,
 events:[{id:'synthetic-income',label:'Synthetic income',date:'2026-10-25',repeat:'once',cents:1}],
 shiftId:'synthetic-income',shiftDays:1};
check(()=>assert.throws(()=>parsePlanJSON(JSON.stringify(baselineOverflow)),/Projected balance exceeds limit/));
check(()=>assert.throws(()=>exportPlan(baselineOverflow),/Projected balance exceeds limit/));
const bytes=new TextEncoder().encode(json);
const file=(data,opts={})=>({name:opts.name??'plan.json',type:opts.type??'application/json',
 size:opts.size??data.length,arrayBuffer:async()=>data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength)});
const asyncChecks=[
 [file(bytes),true],
 [file(bytes,{name:'plan.txt'}),false],
 [file(bytes,{type:'text/html'}),false],
 [file(bytes,{size:bytes.length+1}),false],
 [file(new Uint8Array([0xff,0xfe])),false],
 [file(new Uint8Array(MAX_PLAN_BYTES+1)),false],
 [file(new TextEncoder().encode('{"schema":"cash-flow-plan/v1"}')),false],
 [file(bytes,{type:''}),true]
];
for(const [f,valid] of asyncChecks){
 if(valid){check(async()=>assert.deepEqual(await readPlanFile(f),seed));}
 else{check(async()=>assert.rejects(readPlanFile(f)));}
}
const mismatch={name:'plan.json',type:'',size:bytes.length,arrayBuffer:async()=>new ArrayBuffer(bytes.length-1)};
check(async()=>assert.rejects(readPlanFile(mismatch),/byte count/));
check(()=>assert.equal({}.polluted,undefined));
await Promise.all(pending);
console.log(n+' FT-04 local editable plan validation assertions PASS');
