const assert=require('node:assert/strict');
const G=require('./publication-gate.js');
const known={status:'VERIFIED',source_url:'https://example.edu/official',reporting_year:2025};
const unknown={status:'UNKNOWN'};
function fixture(){
  const cost=Object.fromEntries(['0_30k','30_48k','48_75k','75_110k','110k_plus'].map(k=>[k,null]));
  cost['0_30k']=0;
  const careers={data:null,education:null,health:null,business:null};
  const enrollment={undergraduate:null,total:null};
  const p={setting:unknown,housing:known,access:unknown,aid:unknown};
  for(const k of Object.keys(cost))p['cost.'+k]=k==='0_30k'?{...known,cohort_map_reference:'Synthetic map only'}:unknown;
  for(const k of Object.keys(careers))p['careers.'+k]=unknown;
  for(const k of Object.keys(enrollment))p['enrollment.'+k]=unknown;
  const record={unitid:'123456',name:'Synthetic Test University',publication_status:'APPROVED',publication_approved_by_user:true,field_provenance:p,setting:null,housing:false,access:null,aid:null,cost,careers,enrollment};
  const manifest={schema_version:1,approved_unitids:[{unitid:'123456',approved_by:'user',approved_on:'2026-10-09',approval_reference:'SYNTHETIC TEST ONLY'}]};
  return [{schema_version:1,records:[record]},manifest];
}
assert.equal(G.validate(...fixture()).ok,true);
let [p,m]=fixture();m.approved_unitids=[];assert.equal(G.validate(p,m).ok,false);
[p,m]=fixture();p.records[0].publication_status='DO_NOT_PUBLISH';assert.equal(G.validate(p,m).ok,false);
[p,m]=fixture();p.records[0].publication_approved_by_user=false;assert.equal(G.validate(p,m).ok,false);
[p,m]=fixture();p.records[0].housing=null;p.records[0].field_provenance.housing=unknown;assert.equal(G.validate(p,m).ok,true);
[p,m]=fixture();p.records[0].field_provenance.housing=unknown;assert.equal(G.validate(p,m).ok,false);
[p,m]=fixture();p.records[0].field_provenance['cost.0_30k']=known;assert.equal(G.validate(p,m).ok,false);
[p,m]=fixture();p.records[0].cost['0_30k']=null;p.records[0].field_provenance['cost.0_30k']={...known,status:'SUPPRESSED'};assert.equal(G.validate(p,m).ok,true);
[p,m]=fixture();p.records[0].access=2;p.records[0].field_provenance.access=known;assert.equal(G.validate(p,m).ok,false);
[p,m]=fixture();p.records[0].aid=[];p.records[0].field_provenance.aid=known;assert.equal(G.validate(p,m).ok,false);
[p,m]=fixture();delete p.records[0].field_provenance['enrollment.total'];assert.equal(G.validate(p,m).ok,false);
[p,m]=fixture();p.records[0].enrollment.total=-1;p.records[0].field_provenance['enrollment.total']=known;assert.equal(G.validate(p,m).ok,false);
[p,m]=fixture();p.records[0].testing_policy='optional';assert.equal(G.validate(p,m).ok,false);
[p,m]=fixture();m.approved_unitids.push({...m.approved_unitids[0]});assert.equal(G.validate(p,m).ok,false);
for(const date of ['2026-02-30','2025-02-29','2026-13-01','2026-00-01','0000-01-01','2026-04-31','2026-2-09']){
  const [p,m]=fixture();m.approved_unitids[0].approved_on=date;
  assert.equal(G.validate(p,m).ok,false,'Invalid approval date accepted: '+date);
}
for(const date of ['2024-02-29','2026-10-09']){
  const [p,m]=fixture();m.approved_unitids[0].approved_on=date;
  assert.equal(G.validate(p,m).ok,true,'Valid approval date rejected: '+date);
}
console.log('PASS: 23 synthetic publication-gate JavaScript assertions');
