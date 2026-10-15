'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '../review');
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const files = ['190521','190585','190673'].map(id => 'current-catalog-'+id+'-20261015.json').concat(['current-catalog-190628-a-20261015.json','current-catalog-190628-b-20261015.json']);
const records = files.flatMap(name => read(name).records);
const excluded = ['bmcc-excluded-20261015.json','qcc-excluded-20261015.json'].flatMap(name => read(name).records);
test('exact reviewed coverage, without inflating national counts', () => {
 assert.equal(records.length, 48);
 assert.equal(new Set(records.map(r => r.unitid)).size, 4);
 assert.equal(new Set(records.map(r => r.cip2020)).size, 31);
 assert.equal(new Set(records.map(r => r.unitid+':'+r.plan_code)).size, 48);
 assert.deepEqual(Object.fromEntries(['190521','190585','190628','190673'].map(id => [id, records.filter(r => r.unitid===id).length])), {'190521':11,'190585':12,'190628':9,'190673':16});
});
test('every accepted record has an institutional source and valid identifier', () => {
 const hosts = {'190521':'bmcc.catalog.cuny.edu','190585':'hostos.catalog.cuny.edu','190628':'laguardia.catalog.cuny.edu','190673':'qcc.catalog.cuny.edu'};
 for(const r of records) {
  assert.match(r.unitid, /^\d{6}$/);
  assert.match(r.cip2020, /^\d{2}\.\d{4}$/);
  assert.match(r.nysed_code, /^\d{5}$/);
  assert.notEqual(r.nysed_code,'00000');
  assert.equal(new URL(r.catalog_url).hostname, hosts[r.unitid]);
 }
});
test('catalog plans and CIPs do not imply equivalent credentials', () => {
 assert.equal(records.filter(r=>r.unitid==='190673'&&r.cip2020==='51.3801').length,4);
 assert.equal(records.filter(r=>r.unitid==='190628'&&r.cip2020==='11.1003').length,2);
 assert.equal(records.find(r=>r.unitid==='190521'&&r.plan_code==='LPN-CERT').cip2020,'51.3999');
 assert.equal(records.find(r=>r.unitid==='190628'&&r.plan_code==='PRNRS-CERT').cip2020,'51.3901');
});
test('identity conflicts are excluded', () => {
 assert.equal(excluded.length,2);
 assert.deepEqual(new Set(excluded.map(r=>r.unitid+':'+r.plan_code)),new Set(['190521:NPS-AAS','190673:NP-AAS']));
 assert.equal(excluded.some(q=>records.some(r=>r.unitid===q.unitid&&r.plan_code===q.plan_code)),false);
});
test('review files do not assert admissions, licensure or career eligibility', () => {
 for(const f of files) assert.equal(read(f).evidence_status || 'catalog_listed_not_intake_verified','catalog_listed_not_intake_verified');
 for(const r of records) assert.equal(Object.hasOwn(r,'licensing_eligibility'),false);
});
