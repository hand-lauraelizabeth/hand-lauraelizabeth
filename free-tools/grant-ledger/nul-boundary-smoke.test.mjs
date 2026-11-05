import assert from 'node:assert/strict';
import {calculateLedger} from './core.mjs';
const a={awardId:'A',awardName:'Test',start:'2026-01-01',end:'2026-12-31'};
assert.throws(()=>calculateLedger({...a,awardId:'bad\u0000id'},[],[]),/text of at most/);
console.log('PASS: NUL award ID rejected');
