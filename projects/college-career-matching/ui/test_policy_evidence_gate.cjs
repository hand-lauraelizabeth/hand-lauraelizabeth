const assert = require('node:assert/strict');
const M = require('./applicant-signals.js');
assert.equal(M.testingPolicy({}), 'unknown');
assert.equal(M.validateTesting('omit', '', '').omitted, true);
console.log('PASS: missing testing policy and omitted scores');
