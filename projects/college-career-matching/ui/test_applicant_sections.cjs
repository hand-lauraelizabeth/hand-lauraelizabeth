const assert = require('node:assert/strict');
const signals = require('./applicant-signals.js');
assert.equal(signals.validateGpa('3.5', '4', 'unweighted').ok, true);
console.log('PASS applicant baseline');
