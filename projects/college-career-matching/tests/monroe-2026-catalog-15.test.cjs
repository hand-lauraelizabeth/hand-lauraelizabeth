'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const d=JSON.parse(fs.readFileSync(path.join(__dirname,'../review/monroe-2026-catalog-15.json'),'utf8'));
const m=JSON.parse(fs.readFileSync(path.join(__dirname,'../review/monroe-2026-catalog-15-manifest.json'),'utf8'));
const r=d.records;
test('review counts and unique institution-program identity',()=>{
 assert.equal(r.length,15);assert.equal(m.new_records,15);
 assert.equal(new Set(r.map(x=>x.cip2020)).size,12);
 assert.equal(new Set(r.map(x=>x.unitid+':'+x.program_code)).size,15);
 assert.equal(new Set(r.map(x=>x.unitid)).size,1);
});
test('official catalog provenance and identifiers',()=>{
 for(const x of r){assert.equal(x.unitid,'193326');assert.match(x.cip2020,/^\\d{2}\\.\\d{4}$/);assert.equal(new URL(x.catalog_url).hostname,'notes.monroecc.edu');assert.match(x.catalog_url,/MCCatPub\\.nsf/);assert.equal(x.catalog_year,null);assert.equal(x.source_accessed,'2026-10-15');assert.equal(x.nysed_registrations.every(z=>/^\\d{5}$/.test(z.code)),true);}
});
test('distinct credentials are never collapsed by CIP',()=>{
 const p=r.filter(x=>x.cip2020==='51.0904');assert.deepEqual(new Set(p.map(x=>x.program_code)),new Set(['EM01','EM05','EM02']));
 assert.equal(p.filter(x=>x.credential==='Certificate').length,2);
 const da=r.filter(x=>x.cip2020==='51.0601');assert.equal(da.length,2);assert.notEqual(da[0].program_code,da[1].program_code);
});
test('campus registrations are not treated as separate degrees',()=>{
 const n=r.find(x=>x.program_code==='IN01');assert.deepEqual(n.nysed_registrations,[{campus:'BRI',code:'37194'},{campus:'DCC',code:'37193'}]);assert.equal(m.registration_entries,16);
});
test('no unsupported availability, test policy, licensure or career eligibility',()=>{
 assert.equal(d.publication_status,'review_only_not_live');
 for(const x of r){assert.equal(x.evidence_status,'current_online_catalog_listing_intake_not_verified');assert.equal(x.professional_licensure,'not_independently_verified');assert.equal(Object.hasOwn(x,'admissions_open'),false);assert.equal(Object.hasOwn(x,'sat_act_policy'),false);assert.equal(Object.hasOwn(x,'career_eligibility'),false);}
 assert.equal(m.production_change,false);
});
