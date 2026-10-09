const assert = require('node:assert/strict');
const P = require('./institution-policy.js');
assert.equal(P.match({}, 'test_blind').include, false);
assert.equal(P.match({}, 'omit').include, true);
assert.equal(P.match({testing_policy:'blind',testing_policy_source:'https://example.edu/testing',testing_policy_year:2026,testing_policy_verified:true}, 'test_blind').include, true);
console.log('PASS policy gate');
