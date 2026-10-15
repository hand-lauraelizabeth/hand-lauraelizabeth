'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const d = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'cuny-board-adopted-2026.json'), 'utf8'));
test('2026 policy adoption is explicitly resolved', () => {
  assert.equal(d.undergraduate_sat_act_policy.classification, 'test_optional');
  assert.equal(d.undergraduate_sat_act_policy.adoption_status, 'adopted');
  assert.equal(d.undergraduate_sat_act_policy.adopted_on, '2026-06-29');
  assert.equal(d.undergraduate_sat_act_policy.duration, 'indefinite');
});
test('calendar text and adopted disposition are both cited', () => {
  const sources = d.undergraduate_sat_act_policy.sources;
  assert.equal(sources.length, 3);
  assert.equal(new Set(sources.map(s => s.kind)).size, 3);
  assert(sources.some(s => s.kind === 'official_board_adoption' && s.url.includes('DISPO062926.pdf')));
  assert(sources.some(s => s.kind === 'resolution_text_in_board_calendar' && s.url.includes('CAL0626.pdf')));
});
test('special program exceptions remain separate', () => {
  assert.match(d.undergraduate_sat_act_policy.special_programs, /verified separately/);
  assert.equal(d.safeguards.missing_sat_act_scores_do_not_determine_policy, true);
});
test('Hostos AS approval does not imply catalog availability', () => {
  const p = d.hostos_new_program_board_action;
  assert.equal(p.credential, 'Associate of Science (AS)');
  assert.equal(p.status, 'board_approved_establishment_only');
  assert.equal(p.current_catalog_listing_verified, false);
  assert.equal(p.currently_accepting_applications_verified, false);
  assert.equal(p.cip2020, null);
  assert.equal(p.nysed_program_code, null);
});
test('Hostos dental accreditation stays qualified', () => {
  const a = d.hostos_dental_hygiene_accreditation;
  assert.equal(a.credential, 'AAS');
  assert.equal(a.cip2020, '51.0602');
  assert.equal(a.independent_current_coda_decision_verified, false);
  assert.equal(a.sources.length, 3);
});
test('all evidence links are HTTPS', () => {
  for(const s of d.undergraduate_sat_act_policy.sources) assert.match(s.url, /^https:\/\//);
  for(const u of d.hostos_dental_hygiene_accreditation.sources) assert.match(u, /^https:\/\//);
  assert.match(d.hostos_new_program_board_action.source, /^https:\/\//);
});
test('no production or unsupported crosswalk', () => {
  assert.equal(d.release_effect, 'review_only');
  assert.equal(d.safeguards.no_automatic_unitid_assignment, true);
  assert.equal(d.safeguards.no_program_current_availability_from_board_approval, true);
  assert.equal(d.safeguards.no_individual_licensure_claim, true);
  assert.equal(d.safeguards.no_cip_soc_crosswalk, true);
});
test('national denominator guards', () => {
  assert.deepEqual(d.unchanged_national_denominators, {
    institutions: 6243, numeric_sat_act_overlay_institutions: 1247,
    historical_completion_records: 235330, cip2020_six_digit: 2325
  });
});
