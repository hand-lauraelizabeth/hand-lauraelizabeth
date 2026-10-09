const assert=require('node:assert/strict');
const P=require('./institution-policy.js');
const reviewed=(testing_policy)=>({
  testing_policy,
  testing_policy_source:'https://example.edu/admissions/testing',
  testing_policy_year:2026,
  testing_policy_verified:true
});
assert.equal(P.match({},'omit').include,true);
assert.equal(P.match({},'sat').include,true);
assert.equal(P.match({},'test_optional').include,false);
assert.equal(P.match({},'test_blind').unknown,true);
assert.equal(P.match(reviewed('blind'),'test_blind').include,true);
assert.equal(P.match(reviewed('blind'),'test_optional').include,true);
assert.equal(P.match(reviewed('optional'),'test_optional').include,true);
assert.equal(P.match(reviewed('optional'),'test_blind').include,false);
assert.equal(P.match(reviewed('required'),'test_optional').include,false);
assert.equal(P.match(reviewed('unknown'),'test_optional').include,false);
assert.equal(P.match({...reviewed('blind'),testing_policy_verified:false},'test_blind').include,false);
assert.equal(P.match({...reviewed('blind'),testing_policy_source:''},'test_blind').include,false);
assert.equal(P.match({...reviewed('blind'),testing_policy_year:null},'test_blind').include,false);
assert.equal(P.match({...reviewed('blind'),testing_policy_year:2101},'test_blind').include,false);
assert.equal(P.match({...reviewed('blind'),testing_policy_source:'http://example.edu'},'test_blind').include,false);
assert.equal(P.match(reviewed('blind'),'unexpected').include,false);
assert.match(P.explanation(reviewed('blind'),'sat'),/not considered/);
assert.match(P.explanation({},'sat'),/unverified/);
assert.match(P.explanation(reviewed('optional'),'omit'),/reporting year 2026/);
console.log('PASS: 19 institution-policy provenance and preference assertions');
