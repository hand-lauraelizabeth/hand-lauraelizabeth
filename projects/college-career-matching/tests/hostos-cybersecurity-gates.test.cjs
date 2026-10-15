const test=require('node:test'); const assert=require('node:assert/strict');
const gate=require('../review/hostos-cybersecurity-status-20261015.json');
const d=require('../review/hostos-cybersecurity-2026-source-context.json');
test('No premature registration or catalog claims',()=>{
assert.equal(gate.nysed_registration,null);
assert.equal(gate.cip2020,null);
assert.equal(gate.admissions_open,null);
assert.equal(d.independent_NYSED_registration_proven,false);
assert.equal(d.current_catalog_degree_listing_located,false);
});
test('Keep distinct credential identities',()=>{
assert.equal(d.board_resolution.credential,'AS');
assert.equal(d.distinct_existing_degree.plan,'CSCI-AS');
assert.equal(d.distinct_existing_degree.cip,'11.0701');
});
test('Verify Board facts and catalog source count',()=>{
assert.equal(d.board_resolution.credits,60);
assert.equal(d.board_resolution.major_credits,27);
assert.equal(d.course_pages.length,5);
assert.equal(d.course_existence_is_not_degree_availability,true);
});
test('No unverified awards or release writes',()=>{
assert.equal(d.board_resolution.certification_award_proven,false);
assert.equal(d.board_resolution.NCAE_C_designation_proven,false);
assert.equal(d.no_production_or_crosswalk_change,true);
});
