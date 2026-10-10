"use strict";
/* S2-04 dedicated dependency-free Node unit tests of the actual Sprint 2 core. */
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.join(__dirname,"..");
const html=fs.readFileSync(path.join(root,"college-search-sprint2.html"),"utf8");
const script=html.match(/<script data-college-search>([\s\S]*?)<\/script>/);
assert.ok(script,"Sprint 2 production logic not found");
const browser={};
vm.runInNewContext(script[1],{
  window:browser,document:{getElementById:()=>null},Intl,
},{filename:"college-search-sprint2.js",timeout:2000});
const core=browser.CollegeSearchCore;
for(const method of ["filterSchools","matchesSizeBand","resetFilterOptions","validatePayload","countUnknowns"])
  assert.equal(typeof core[method],"function",method);
const make=(id,name,state,control,locale,size)=>({
  unitid:id,name,city:"Example City",state,url:null,
  control,locale,undergraduate_size:size
});
const sample=[
  make("100001","Alpha College","NY","public","city",0),
  make("100002","Alpha Academy","NY","public","suburb",4999),
  make("100003","Beta College","CA","private_nonprofit","town",5000),
  make("100004","Beta Institute","NY","private_nonprofit","rural",14999),
  make("100005","Gamma University","NY","private_for_profit","city",15000),
  make("100006","Gamma College","CA","private_for_profit","suburb",30000),
  make("100007","Delta College","NY",null,"city",null),
  make("100008","Delta Institute","NY","public",null,null),
  make("100009","Echo College","CA","public","town",14999),
  make("100010","Echo Institute","NY","private_nonprofit",null,15000),
  make("100011","Zeta University","NY",null,null,4999),
  make("100012","Zeta College","CA","public","rural",null),
];
const ids=items=>Array.from(items,r=>r.unitid);
const sorted=values=>[...values].sort();
const filter=(options={},rows=sample)=>ids(core.filterSchools(
  rows,{...core.resetFilterOptions(),...options}
));
const v2=JSON.parse(fs.readFileSync(path.join(root,"data/sprint2/college-search-national.v2.json"),"utf8"));
const source=Object.values(v2.institutions);
assert.equal(source.length,6243,"Full national source required");
const national=core.validatePayload(v2);
const nationalCount=(options={})=>filter(options,national).length;

test("defaults keep all records including missing new-field values",()=>{
  const options=core.resetFilterOptions();
  for(const key of ["name","state","control","locale","size"])assert.equal(options[key],"");
  assert.equal(options.sort,"name-asc");
  assert.equal(filter().length,12);
  assert.equal(nationalCount(),6243);
});
const controls=[
  ["public",["100001","100002","100008","100009","100012"]],
  ["private_nonprofit",["100003","100004","100010"]],
  ["private_for_profit",["100005","100006"]],
];
for(const [value,expected] of controls)
  test("control alone: "+value,()=>{
    assert.deepEqual(sorted(filter({control:value})),expected);
    assert.ok(!filter({control:value}).includes("100007"),"Null control excluded");
  });
const locales=[
  ["city",["100001","100005","100007"]],
  ["suburb",["100002","100006"]],
  ["town",["100003","100009"]],
  ["rural",["100004","100012"]],
];
for(const [value,expected] of locales)
  test("locale alone: "+value,()=>{
    assert.deepEqual(sorted(filter({locale:value})),expected);
    for(const id of ["100008","100010","100011"])
      assert.ok(!filter({locale:value}).includes(id),"Null locale excluded");
  });
const bands=[
  ["under-5000",["100001","100002","100011"]],
  ["5000-14999",["100003","100004","100009"]],
  ["15000-plus",["100005","100006","100010"]],
];
for(const [value,expected] of bands)
  test("undergraduate size alone: "+value,()=>{
    assert.deepEqual(sorted(filter({size:value})),expected);
    for(const id of ["100007","100008","100012"])
      assert.ok(!filter({size:value}).includes(id),"Null size excluded");
  });
test("size bands use boundaries 0/4,999/5,000/14,999/15,000",()=>{
  for(const [n,selected] of [
    [0,"under-5000"],[4999,"under-5000"],
    [5000,"5000-14999"],[14999,"5000-14999"],
    [15000,"15000-plus"],[100000,"15000-plus"],
  ]){
    for(const [band] of bands)
      assert.equal(core.matchesSizeBand(n,band),band===selected,
        "Incorrect classification for "+n+" in "+band);
  }
});
test("unknown/invalid size never enters a selected size band",()=>{
  for(const [band] of bands)
    for(const n of [null,undefined,-1,"4999",NaN])
      assert.equal(core.matchesSizeBand(n,band),false,
        "Invalid enrollment accepted by "+band);
  assert.equal(core.matchesSizeBand(null,""),true,"All sizes includes null");
});
test("name and state combine with control and exclude incompatible rows",()=>{
  assert.deepEqual(sorted(filter({name:"alpha",state:"NY",control:"public"})),
    ["100001","100002"]);
  assert.deepEqual(filter({name:"alpha",state:"CA",control:"public"}),[]);
});
test("name and state combine with locale",()=>{
  assert.deepEqual(filter({name:"beta",state:"NY",locale:"rural"}),["100004"]);
  assert.deepEqual(filter({name:"beta",state:"CA",locale:"rural"}),[]);
});
test("name and state combine with size bands",()=>{
  assert.deepEqual(filter({name:"beta",state:"CA",size:"5000-14999"}),["100003"]);
  assert.deepEqual(filter({name:"beta",state:"CA",size:"under-5000"}),[]);
});
test("all new fields AND name AND state produce one exact result",()=>{
  assert.deepEqual(filter({name:"college",state:"NY",control:"public",
    locale:"city",size:"under-5000"}),["100001"]);
  assert.deepEqual(filter({name:"institute",state:"NY",control:"private_nonprofit",
    locale:"rural",size:"5000-14999"}),["100004"]);
  assert.deepEqual(filter({name:"university",state:"NY",control:"private_for_profit",
    locale:"city",size:"15000-plus"}),["100005"]);
});
test("contradictions, missing names and zero-result paths never fall back",()=>{
  assert.deepEqual(filter({control:"private_nonprofit",locale:"city"}),[]);
  assert.deepEqual(filter({name:"does not exist",state:"NY",size:"15000-plus"}),[]);
  assert.deepEqual(filter({name:"college",state:"NY",control:"private_for_profit",
    locale:"rural",size:"under-5000"}),[]);
});
test("case-insensitive name and exact state behavior survive new filters",()=>{
  assert.deepEqual(sorted(filter({name:"  ALPHA  ",state:"NY",
    control:"public",size:"under-5000"})),["100001","100002"]);
  assert.deepEqual(filter({name:"Ithaca",state:"NY",control:"public"}),[]);
});
test("sorting and filtering do not mutate original data",()=>{
  const before=JSON.stringify(sample);
  const asc=filter({control:"public",sort:"name-asc"});
  const desc=filter({control:"public",sort:"name-desc"});
  assert.deepEqual(desc,[...asc].reverse());
  assert.equal(JSON.stringify(sample),before);
});
test("missing source fields have transparent counts",()=>{
  assert.deepEqual(JSON.parse(JSON.stringify(core.countUnknowns(sample))),
    {total:12,control:2,locale:3,size:3});
  assert.deepEqual(JSON.parse(JSON.stringify(core.countUnknowns(national))),
    {total:6243,control:0,locale:531,size:781});
});
test("national results independently match per-option source counts",()=>{
  const grouped={control:controls.map(x=>x[0]),
    locale:locales.map(x=>x[0]),size:bands.map(x=>x[0])};
  for(const [field,values] of Object.entries(grouped))
    for(const value of values){
      const expected=source.filter(r=>
        field==="size"?core.matchesSizeBand(r.undergraduate_size,value):
          r[field]===value).length;
      assert.equal(nationalCount({[field]:value}),expected,field+"/"+value);
      assert.ok(expected>0&&expected<6243,field+"/"+value+" must change results");
    }
});
test("national combined name/state/control/locale/size independently agrees",()=>{
  const options={name:"University",state:"NY",control:"public",
    locale:"city",size:"15000-plus"};
  const independent=source.filter(r=>r.name.toLowerCase().includes("university") &&
    r.state==="NY"&&r.control==="public"&&r.locale==="city"&&
    r.undergraduate_size!==null&&r.undergraduate_size>=15000).length;
  assert.equal(nationalCount(options),independent);
  assert.equal(independent,0,"This legitimate real-data intersection has no matching schools");
});
test("schema rejects omission of each new field without substitution",()=>{
  for(const field of ["control","locale","undergraduate_size"]){
    const [id,row]=Object.entries(v2.institutions)[0];
    const broken={...v2,institutions:{...v2.institutions,[id]:{...row}}};
    delete broken.institutions[id][field];
    assert.throws(()=>core.validatePayload(broken),/institution record failed validation/i,
      "Missing "+field);
  }
});
test("reset restores defaults independently of previous selections",()=>{
  const prev=core.resetFilterOptions();
  Object.assign(prev,{name:"Alpha",control:"public",locale:"city",
    size:"under-5000"});
  assert.deepEqual(filter(prev),["100001"]);
  const clean=core.resetFilterOptions();
  for(const field of ["name","state","control","locale","size"])
    assert.equal(clean[field],"");
  assert.equal(clean.sort,"name-asc");
  assert.equal(filter(clean).length,sample.length);
});
