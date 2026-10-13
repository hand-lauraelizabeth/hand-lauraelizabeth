'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const evidence = JSON.parse(fs.readFileSync(path.join(__dirname, '../data/review/dda-school-credentials-20261013-11ET.json'), 'utf8'));
assert.equal(evidence.status, 'review_only');
assert.equal(evidence.records.length, 2);
assert.equal(new Set(evidence.records.map(r => r.unitid)).size, 2);
assert.deepEqual(evidence.records.map(r => r.unitid).sort(), ['260664','373526']);
for (const row of evidence.records) {
  assert.match(row.unitid, /^\d{6}$/);
  assert.equal(row.school_award, 'Certificate of Completion');
  assert.equal(row.school_award_verified_for_2026_27, false);
  assert.equal(row.licensure_equivalence, false);
  assert.equal(row.sat_act_policy, 'unknown');
  assert.match(row.school_award_catalog_url, /^https:\/\/dda\.edu\//);
  assert.match(row.current_program_url, /^https:\/\/dda\.edu\//);
  assert.deepEqual(Object.values(row.program_hours_by_catalog).sort((a,b)=>a-b), [136,160,600]);
}
assert.equal(evidence.coverage.current_live_changes, 0);
assert.equal(evidence.coverage.verified_2026_27_awards, 0);
console.log('PASS: DDA school credential review evidence');
