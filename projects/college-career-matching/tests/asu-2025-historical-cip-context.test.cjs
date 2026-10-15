'use strict';
const a=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const d=require('../review/asu-2025-historical-cip-context.json'),root=path.resolve(__dirname,'../../..');
a.equal(d.pinned_release_commit,'3abb9f458c9d0d43c857c64292dc407f3bd1e911');
a.equal(d.national_denominators.scorecard_institutions,6243);
a.equal(d.national_denominators.historical_cip_awlevel_rows,235330);
a.deepEqual(d.observations.map(x=>x.unitid),['104151','483124']);
a.deepEqual(d.observations.map(x=>x.total_historical_cip_awlevel_rows),[492,243]);
a.equal(d.reviewed_catalog_plan_codes.length,9);
a.deepEqual(d.catalog_plan_to_cip_mapping,{});
a.deepEqual(d.catalog_plan_to_unitid_award_row_mapping,{});
a.equal(d.current_catalog_availability_verified_by_ipeds,false);
a.equal(d.professional_license_eligibility_verified_by_ipeds,false);
const m=JSON.parse(fs.readFileSync(path.join(root,d.source_manifest))),titles=JSON.parse(fs.readFileSync(path.join(root,d.source_cip_titles)));
a.equal(Object.keys(titles).length,2325);
for(const o of d.observations){
 const raw=fs.readFileSync(path.join(root,o.source_shard));
 a.equal(crypto.createHash('sha256').update(raw).digest('hex'),o.source_shard_sha256);
 a.equal(m.shards.find(x=>o.source_shard.endsWith(x.file)).sha256,o.source_shard_sha256);
 const e=JSON.parse(raw).institutions.find(x=>x[0]===o.unitid);
 a.ok(e);a.equal(e[1].length,o.total_historical_cip_awlevel_rows);
 a.equal(o.observed_bachelors.length,8);
 for(const r of o.observed_bachelors){
  a.equal(titles[r.cip6],r.official_cip2020_title);
  a.deepEqual(e[1].filter(x=>x[0]===r.cip6&&x[1]==='5'),[[r.cip6,'5',r.awards_conferred,'reported']]);
 }
}
a.equal(d.observations[1].observed_bachelors.find(x=>x.cip6==='140501').awards_conferred,0);
console.log('ASU pinned-source, CIP title, hash and nonjoin safeguards passed');
