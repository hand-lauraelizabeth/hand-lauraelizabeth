// Synthetic-only evidence provenance contract; no personal records.
import assert from 'node:assert/strict';
import {parseWorkspaceJSON} from './import.mjs';
import {exportJSON} from './core.mjs';
const valid={version:1,requests:[{id:'REQ-0001',jurisdiction:'federal',agency:'Example Agency',stage:'draft',submittedOn:'',agencyTrackingId:'0000123',description:'Quoted {key}, Unicode café and \\ slash'}],events:[]};
const serialized=JSON.stringify(valid);
let checks=0;
const check=(fn)=>{fn();checks++};
check(()=>assert.deepEqual(parseWorkspaceJSON(serialized),valid));
check(()=>assert.deepEqual(parseWorkspaceJSON(exportJSON(valid)),valid));
const dupes=[
  '{"version":0,"version":1,"requests":[],"events":[]}',
  '{"version":1,"requests":[],"events":[],"events":[]}',
  serialized.replace('"id":"REQ-0001"','"id":"SHADOW","id":"REQ-0001"'),
  serialized.replace('"id":"REQ-0001"','"id":"SHADOW","\\u0069d":"REQ-0001"'),
  serialized.replace('"agencyTrackingId":"0000123"','"agencyTrackingId":"999","agencyTrackingId":"0000123"'),
  serialized.replace('"description":"Quoted','"description":"SHADOW","description":"Quoted'),
];
for (const [i,raw] of dupes.entries()) check(()=>assert.throws(()=>parseWorkspaceJSON(raw),/Duplicate JSON object key/,`duplicate case ${i}`));
check(()=>assert.equal(parseWorkspaceJSON(serialized).requests[0].id,'REQ-0001'));
console.log('PASS: '+checks+' strict duplicate-key import assertions');
