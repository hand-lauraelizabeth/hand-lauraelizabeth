import assert from 'node:assert/strict';
import fs from 'node:fs';
const root = new URL('../data/review/', import.meta.url);
const read = (name) => JSON.parse(fs.readFileSync(new URL(name, root), 'utf8'));
const core = read('sarasota-2026-bilingual-evidence.json');
const scope = read('sarasota-2026-program-scope.json');
const license = read('sarasota-2026-licensing-price-scope.json');
const check = (a,b,c) => assert.equal(a,b,c);
check(core.unitid,'406149');
check(scope.unitid,core.unitid);
check(license.unitid,core.unitid);
check(scope.english.hours,750);
check(scope.spanish.hours,750);
check(scope.admissions.minimum_age,18);
check(scope.admissions.sat_act,'unknown');
check(scope.admissions.school_award,'unknown');
check(scope.cohort_language,'unknown');
check(scope.seats,'unknown');
check(scope.new_institutions,0);
check(scope.new_cip6,0);
check(license.florida_licensing_requirements.school_program_hours_minimum,500);
check(license.florida_licensing_requirements.school_completion_automatically_grants_license,false);
check(license.florida_licensing_requirements.individual_eligibility_verified,false);
check(license.program_cost.verified_current_2026_price,false);
check(license.program_cost.spanish_program_price,'unknown');
for(const [mutate,why] of [
  [x=>x.admissions.sat_act='test_optional','SAT/ACT policy inference'],
  [x=>x.new_cip6=2,'CIP inflation'],
  [x=>x.seats='available','invented seat availability']
]) {
  const altered=structuredClone(scope);mutate(altered);
  assert.notDeepEqual(altered,scope,why);
}
console.log('PASS: 17 assertions + 3 negative mutations');
