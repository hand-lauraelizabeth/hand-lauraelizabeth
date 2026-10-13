'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const data = JSON.parse(fs.readFileSync(path.join(__dirname,'../data/review/institutional-certification-eligibility-20261013-15ET.json'),'utf8'));
assert.equal(data.records.length,2);
assert.equal(new Set(data.records.map(x=>x.unitid)).size,2);
for (const record of data.records) {
  assert.match(record.unitid,/^\d{6}$/);
  assert.equal(record.school_issued_award_title,null);
  assert.equal(record.school_award_verification,'unverified');
  assert.equal(record.license_eligibility,'not_verified');
  assert.notEqual(record.sat_act_policy,'test_blind');
}
const northwestern = data.records.find(x=>x.unitid==='168573');
assert.equal(northwestern.program_name,'Climate Control Technology');
assert.equal(northwestern.professional_certification_status,'preparation_for_exams_only');
assert.equal(northwestern.professional_certifications_issued_by_school,false);
assert.equal(northwestern.professional_certification_exams.length,4);
assert.equal(northwestern.sat_act_policy,'unknown');
const ocean = data.records.find(x=>x.unitid==='227298');
assert.equal(ocean.sat_act_policy,'not_required_to_apply');
assert.match(ocean.imca_card_status,/qualifying_dives/);
assert.ok(ocean.sources.every(x=>x.url.startsWith('https://oceancorp.com/')));
assert.ok(Object.values(data.guards).every(x=>x===false));
console.log('PASS: 15 certification evidence and non-inference checks');
