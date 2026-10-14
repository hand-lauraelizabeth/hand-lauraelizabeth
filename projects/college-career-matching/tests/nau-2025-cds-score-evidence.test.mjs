import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const evidence = JSON.parse(readFileSync(new URL('../data/review/nau-2025-cds-score-candidate.json', import.meta.url), 'utf8'));
const clone = (x) => structuredClone(x);
const assertValid = (d) => {
  assert.match(d.institution.unitid, /^\d{6}$/);
  assert.equal(d.institution.unitid, '105330');
  assert.equal(d.institution.present_in_pinned_national_v3, true);
  assert.equal(d.institution.absent_from_pinned_score_overlay_v3, true);
  assert.equal(d.reconciliation.exact_unitid_in_national, true);
  assert.equal(d.reconciliation.exact_unitid_in_overlay, false);
  assert.equal(d.reconciliation.national_v3_institutions, 6243);
  assert.equal(d.reconciliation.score_v3_institutions, 1247);
  assert.equal(d.state, 'review_only');
  assert.equal(d.safety.auto_merge_into_pinned_overlay, false);
  assert.equal(d.safety.automatic_safety_target_reach, false);
  assert.equal(d.safety.display_mode, 'descriptive_only');
  assert.equal(d.admissions.policy, 'test_optional_considered_if_submitted');
  assert.equal(d.admissions.require_sat_act_for_general_admission, false);
  assert.equal(d.admissions.uses_sat_act_for_admission, true);
  assert.equal(d.submissions.sat.count, 154);
  assert.equal(d.submissions.sat.percent_rounded, 3);
  assert.equal(d.submissions.act.count, 1239);
  assert.equal(d.submissions.act.percent_rounded, 27);
  assert.deepEqual([d.scores.sat_composite.p25,d.scores.sat_composite.p50,d.scores.sat_composite.p75],[1010,1175,1280]);
  assert.deepEqual([d.scores.act_composite.p25,d.scores.act_composite.p50,d.scores.act_composite.p75],[19,23,26]);
  for (const [name,values] of Object.entries(d.scores)) {
    const {p25,p50,p75}=values;
    if ([p25,p50,p75].every(v=>v!==null)) {
      assert.ok(p25<=p50 && p50<=p75, name+' percentiles ordered');
      assert.ok(p25>=0 && p75<=(name.startsWith('sat_')?1600:36),name+' score bounds');
    }
  }
  assert.equal(d.scores.act_writing.p75, null);
  assert.equal(d.safety.derived_sat_average, null);
  assert.equal(d.safety.derived_act_average, null);
  assert.equal(d.source.sections.includes('C8F'), true);
  assert.equal(d.source.sections.includes('C9'), true);
  assert.match(d.source.url, /^https:\/\/in\.nau\.edu\//);
};

test('source-aware Fall 2025 NAU score evidence passes all gates',()=>assertValid(evidence));
for (const [label, mutate] of [
  ['reject eight-digit extension',d=>{d.institution.unitid='10533001'}],
  ['reject missing official source',d=>{d.source.url='https://example.org/'}],
  ['reject fabricated SAT mean',d=>{d.safety.derived_sat_average=1175}],
  ['reject invented ACT writing percentile',d=>{d.scores.act_writing.p75=25}],
  ['reject inferred mandatory test policy',d=>{d.admissions.require_sat_act_for_general_admission=true}],
  ['reject automatic admission categories',d=>{d.safety.automatic_safety_target_reach=true}],
  ['reject overlay overwrite',d=>{d.safety.auto_merge_into_pinned_overlay=true}],
  ['reject invalid SAT percentiles',d=>{d.scores.sat_composite.p25=1400}],
  ['reject changed score sample',d=>{d.submissions.act.count=12}]
]) {
  test(label,()=>{const d=clone(evidence);mutate(d);assert.throws(()=>assertValid(d));});
}
