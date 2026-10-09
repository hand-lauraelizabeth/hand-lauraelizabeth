const assert=require('node:assert/strict');
const M=require('./applicant-signals.js');
assert.match(M.policyNote({},'omit'),/Policy source or reporting year unavailable/);
console.log('PASS missing policy provenance');
