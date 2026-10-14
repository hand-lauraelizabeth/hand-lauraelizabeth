import assert from 'node:assert/strict';
import fs from 'node:fs';
const root = new URL('../data/review/', import.meta.url);
const read = name => JSON.parse(fs.readFileSync(new URL(name,root),'utf8'));
const core=read('sarasota-2026-bilingual-evidence.json');
const scope=read('sarasota-2026-program-scope.json');
const gate=read('sarasota-2026-licensing-price-scope.json');
const qa=read('sarasota-2026-catalog-hours-qa.json');
function validate(s,g,q) {
  assert.equal(s.unitid,'406149');
  assert.equal(s.english.hours,750);
  assert.equal(s.spanish.hours,750);
  assert.equal(s.admissions.sat_act,'unknown');
  assert.equal(s.admissions.school_award,'unknown');
  assert.equal(s.seats,'unknown');
  assert.equal(s.cohort_language,'unknown');
  assert.equal(s.new_institutions,0);
  assert.equal(s.new_cip6,0);
  assert.equal(g.florida_licensing_requirements.school_completion_automatically_grants_license,false);
  assert.equal(g.program_cost.verified_current_2026_price,false);
  assert.equal(q.spanish.subject_subtotals.reduce((a,b)=>a+b,0),735);
  assert.equal(q.spanish.claimed_total-q.spanish.calculated_total,15);
  assert.equal(q.english.subject_subtotals.reduce((a,b)=>a+b,0),750);
}
assert.equal(core.unitid,scope.unitid);
assert.equal(scope.unitid,gate.unitid);
assert.equal(gate.unitid,qa.unitid);
validate(scope,gate,qa);
const mutations=[
  [s=>s.admissions.sat_act='test_optional',g=>g,q=>q],
  [s=>s.new_cip6=2,g=>g,q=>q],
  [s=>s.seats='available',g=>g,q=>q],
  [s=>s,g=>g.florida_licensing_requirements.school_completion_automatically_grants_license=true,q=>q],
  [s=>s,g=>g,q=>q.spanish.calculated_total=750]
];
for(const [changeS,changeG,changeQ] of mutations) {
 const s=structuredClone(scope),g=structuredClone(gate),q=structuredClone(qa);
 changeS(s);changeG(g);changeQ(q);
 assert.throws(()=>validate(s,g,q),assert.AssertionError);
}
console.log('PASS 17 positive assertions and 5 negative mutations');
