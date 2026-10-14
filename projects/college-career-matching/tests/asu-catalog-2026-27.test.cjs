const assert=require('node:assert/strict');
const base='../review/';
const files=['asu-catalog-status-closed-and-biomedical-20261014.json','asu-catalog-computing-2026-27.json','asu-catalog-data-software-health-2026-27.json'];
const docs=files.map(f=>require(base+f));
const rows=docs.flatMap(d=>d.records);
assert.equal(rows.length,9);
assert.equal(rows.filter(r=>r.status==='catalog_listed').length,8);
assert.equal(rows.filter(r=>r.status==='closed_to_new_students').length,1);
assert.equal(new Set(rows.map(r=>r.plan)).size,9);
for(const d of docs){assert.equal(d.campus_join_verified,false);assert.equal(d.all_cip_codes_unverified,true);}
const byPlan=Object.fromEntries(rows.map(r=>[r.plan,r]));
assert.equal(byPlan.ASACOCBS.status,'closed_to_new_students');
assert.notEqual(byPlan.TSSERBS.plan,byPlan.ESCSESBS.plan);
assert.ok(byPlan.ESBMEBSE.admissions_note.includes('or'));
console.log('ASU catalog evidence tests passed');
