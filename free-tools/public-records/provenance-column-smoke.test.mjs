import assert from 'node:assert/strict';
import test from 'node:test';
import { exportCSV } from './core.mjs';
const w={version:1,requests:[{id:'R001',jurisdiction:'federal',agency:'Sample Office',stage:'submitted',submittedOn:'2026-10-20',agencyTrackingId:'000019',description:'Sample'}],events:[{id:'E001',requestId:'R001',date:'2026-10-21',kind:'note',sourceId:'SRC001',description:'Sample'}]};
test('CSV distinguishes tracking IDs from source IDs',()=>{
 const [head,req,event]=exportCSV(w).trimEnd().split('\r\n').map(line=>line.split(',').map(cell=>cell.slice(1,-1)));
 assert.equal(head.length,11);
 assert.equal(req[8],'');
 assert.equal(req[10],'000019');
 assert.equal(event[8],'SRC001');
 assert.equal(event[10],'');
});