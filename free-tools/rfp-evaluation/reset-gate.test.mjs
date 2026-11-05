import assert from 'node:assert/strict';
import {createResetGate} from './reset-gate.mjs';
const gate=createResetGate();
const p=gate.stage({criterion:1,vendor:2,rating:3});
assert.equal(p.total,6);
assert.deepEqual(gate.take(p.token),{criterion:1,vendor:2,rating:3});
assert.throws(()=>gate.take(p.token),/no longer current/);
