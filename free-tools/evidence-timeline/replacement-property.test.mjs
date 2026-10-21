import assert from 'node:assert/strict';
import {previewReplacement, replacementConfirmation} from './replacement-preview.mjs';
// Deterministic synthetic fixtures; source identifiers remain exact.
let seed = 0x17a1c05;
const rand = () => {seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5; return seed >>> 0;};
const ids = ['000123','123',' A ','A','caf\u00e9','cafe\u0301','case','CASE','ID-9','10','01'];
const row = (sourceId,claim) => ({sourceId,date:'2026-10-17',claim,status:'reported',kind:'source',group:''});
let checks = 0;
for (let n=0;n<200;n++) {
  const old = ids.filter(()=>rand()%3!==0).map(id=>row(id,String(rand()%3)));
  const next = ids.filter(()=>rand()%3!==0).map(id=>row(id,String(rand()%3)));
  const before = JSON.stringify([old,next]);
  const oldMap = new Map(old.map(r=>[r.sourceId,r]));
  const newMap = new Map(next.map(r=>[r.sourceId,r]));
  const expected = {existing:old.length,incoming:next.length,added:0,removed:0,changed:0,unchanged:0};
  for (const [id,r] of newMap) {
    if (!oldMap.has(id)) expected.added++;
    else if (oldMap.get(id).claim!==r.claim) expected.changed++;
    else expected.unchanged++;
  }
  for (const id of oldMap.keys()) if (!newMap.has(id)) expected.removed++;
  const actual = previewReplacement(old,next);
  assert.deepEqual(actual,expected); checks++;
  assert.equal(actual.added+actual.changed+actual.unchanged,actual.incoming); checks++;
  assert.equal(actual.removed+actual.changed+actual.unchanged,actual.existing); checks++;
  assert.equal(JSON.stringify([old,next]),before); checks++;
  assert.ok(!replacementConfirmation(actual).includes('Synthetic')); checks++;
}
console.log('PASS: '+checks+' synthetic replacement-property assertions');
