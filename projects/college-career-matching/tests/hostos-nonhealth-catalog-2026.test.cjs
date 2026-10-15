'use strict';
const assert = require('node:assert/strict');
const data = require('../data/hostos-nonhealth-catalog-2026.json');
const expected = {
  'CSCI-AS':['Computer Science','AS','11.0701','41070 - CSCI-AS'],
  'GAME-AAS':['Game Design','AAS','50.0411','34999 - GAME-AAS'],
  'DD-AAS':['Digital Design and Animation','AAS','10.0304','32620 - DD-AAS'],
  'CIVENGR-AS':['Civil Engineering Science','AS','14.0801','29493 - CVLEH-BE'],
  'ACCT-AAS':['Accounting','AAS','52.0302','00908 - ACCT-AAS'],
  'ACCT-AS':['Accounting','AS','52.0302','32630 - ACCT-AS'],
  'ACCTFOR-AS':['Accounting for Forensic Accounting','AS','52.0301','33416 - ECOHOST-BS'],
  'BUSMGT-AS':['Business Management','AS','52.0201','83164 - BUSMGT-AS']
};
assert.equal(data.catalog_year,'2026-2027');
assert.equal(data.records.length,8);
assert.equal(new Set(data.records.map(r=>r.plan)).size,8);
for(const r of data.records) {
  assert.deepEqual([r.name,r.credential,r.cip,r.nysed],expected[r.plan]);
  assert.equal(r.catalog,'https://hostos.catalog.cuny.edu/programs/'+r.plan);
  assert.equal(r.admission_status,'unverified');
}
assert.equal(data.records.filter(r=>r.cip==='52.0302').length,2);
assert.equal(data.limitations.historical_completions,'not joined');
assert.equal(data.limitations.licensure,'not inferred');
assert.equal(data.limitations.test_policy,'not inferred');
assert.equal(data.limitations.cip_soc,'not mapped');
console.log('PASS: eight Hostos catalog records and separate credential, CIP, admissions and licensure evidence');
