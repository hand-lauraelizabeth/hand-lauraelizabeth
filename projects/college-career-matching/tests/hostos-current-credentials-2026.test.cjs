'use strict';
const assert=require('node:assert/strict');
const x=require('../data/hostos-current-credentials-2026.json');
assert.equal(x.records.length,4);
assert.equal(new Set(x.records.map(r=>r.plan)).size,4);
const expected={'NURS-AAS':['51.3801','83183','AAS'],'LPN-CERT':['51.3901','22104','Certificate'],'XRAY-AAS':['51.0907','00913','AAS'],'DENHYG-AAS':['51.0602','00911','AAS']};
for(const r of x.records){
 assert.deepEqual([r.cip,r.nysed,r.credential],expected[r.plan]);
 assert.match(r.catalog,/^https:\/\/hostos\.catalog\.cuny\.edu\/programs\//);
 assert.ok(r.regulator.startsWith('https://'));
}
assert.equal(x.unitid,null);
assert.equal(x.limitations.sat_act_policy,'not inferred');
assert.equal(x.limitations.license_eligibility,'not inferred');
assert.equal(x.limitations.ipeds_program_mapping,'not inferred');
assert.equal(x.limitations.career_mapping,'not inferred');
assert.match(x.records.find(r=>r.plan==='DENHYG-AAS').status,/pending/);
console.log('PASS: 4 current Hostos credentials, exact catalog CIP and NYSED identifiers, provenance and scope boundaries');
