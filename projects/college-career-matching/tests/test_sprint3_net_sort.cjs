"use strict";
const fs=require("node:fs"), path=require("node:path"), assert=require("node:assert/strict"), vm=require("node:vm");
const base=path.resolve(__dirname,"..");
const js=fs.readFileSync(path.join(base,"college-search-sprint3-embed.js"),"utf8");
const sandbox={window:{},document:{getElementById:()=>null},Intl,Number,Object,Set,Array,String,Math,console};
vm.runInNewContext(js,sandbox,{filename:"college-search-sprint3-embed.js"});
const core=sandbox.window.CollegeSearchCore;
assert(core && typeof core.filterSchools==="function");
const data=JSON.parse(fs.readFileSync(path.join(base,"data/sprint3/college-search-national.v3.json"),"utf8"));
const records=core.validatePayload(data);
assert.equal(records.length,6243);
const options=core.resetFilterOptions();
const asc=core.filterSchools(records,{...options,sort:"net-asc"});
const desc=core.filterSchools(records,{...options,sort:"net-desc"});
assert.equal(asc.length,6243);
assert.equal(desc.length,6243);
const available=asc.filter(r=>r.average_net_price!==null);
const missing=asc.filter(r=>r.average_net_price===null);
assert.equal(available.length,5021);
assert.equal(missing.length,1222);
assert(available.some(r=>r.average_net_price<0),"Do not discard published negative net price");
assert(available.every((r,i)=>!i||available[i-1].average_net_price<=r.average_net_price),"Ascending order must be nondecreasing");
assert(desc.slice(0,5021).every((r,i,a)=>!i||a[i-1].average_net_price>=r.average_net_price),"Descending order must be nonincreasing");
assert(asc.slice(-1222).every(r=>r.average_net_price===null),"Unknowns last in low-high");
assert(desc.slice(-1222).every(r=>r.average_net_price===null),"Unknowns last in high-low");
assert.equal(asc[0].average_net_price,Math.min(...available.map(r=>r.average_net_price)));
assert.equal(desc[0].average_net_price,Math.max(...available.map(r=>r.average_net_price)));
const sortedWithState=core.filterSchools(records,{...options,state:"NY",control:"private_nonprofit",sort:"net-asc"});
const expectedNY=records.filter(r=>r.state==="NY"&&r.control==="private_nonprofit");
assert.equal(sortedWithState.length,expectedNY.length);
assert(sortedWithState.every((r,i)=>!i||r.average_net_price===null||
  (sortedWithState[i-1].average_net_price!==null &&
  sortedWithState[i-1].average_net_price<=r.average_net_price)),"State/control combinations remain sorted");
const filtered=core.filterSchools(records,{...options,netMax:20000,sort:"net-desc"});
assert.equal(filtered.length,3083);
assert(filtered.every((r,i)=>r.average_net_price!==null && r.average_net_price<=20000 &&
  (!i||filtered[i-1].average_net_price>=r.average_net_price)));
const a=core.filterSchools(records,{...options,sort:"name-asc"});
const z=core.filterSchools(records,{...options,sort:"name-desc"});
assert.equal(a.length,6243);
assert.equal(z.length,6243);
assert.equal(a[0].unitid,z[z.length-1].unitid);
assert.equal(core.resetFilterOptions().sort,"name-asc");
console.log("S3_NET_PRICE_SORT_UNIT_PASS",JSON.stringify({
  rows:records.length,priced:available.length,unknown:missing.length,
  min:asc[0].average_net_price,max:desc[0].average_net_price,
  filteredUnder20000:filtered.length
}));
