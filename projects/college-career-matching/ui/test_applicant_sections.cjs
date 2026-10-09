const assert = require('node:assert/strict');
const signals = require('./applicant-signals.js');
assert.equal(signals.validateGpa('3.5', '4', 'unweighted').ok, true);
assert.equal(signals.validateTesting('sat','1200','',{satReadingWriting:'600',satMath:'600'}).ok,true);
console.log('PASS applicant baseline');
