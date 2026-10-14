import assert from 'node:assert/strict';
import { weightedScore } from './weights.mjs';
const criteria = [{id:'technical',weight:60},{id:'support',weight:40}];
const ratings = [{criterionId:'technical',score:4,evidenceRef:'S1'},{criterionId:'support',score:3,evidenceRef:'S2'}];
assert.equal(weightedScore(criteria,ratings),72);
assert.equal(weightedScore(criteria,[ratings[0]]),null);
assert.equal(weightedScore(criteria,[{...ratings[0],evidenceRef:''},ratings[1]]),null);
assert.throws(()=>weightedScore([{id:'x',weight:90}],[]));
console.log('FT-07 weighted-score checks: 4 PASS');
