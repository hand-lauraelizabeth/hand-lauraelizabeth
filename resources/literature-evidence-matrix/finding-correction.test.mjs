import test from "node:test";
import assert from "node:assert/strict";
import {SCHEMA,updateClaim,analyzeProject,exportProject,importProject} from "./core.mjs";
const p={schema:SCHEMA,sources:[{id:"0001",title:"Synthetic source",year:null,doi:""},{id:"β-02",title:"Second synthetic source",year:null,doi:""}],claims:[{id:"finding-001",sourceId:"0001",question:"Q",summary:"Original",stance:"supports",locator:"p. 1",methods:"Method A",limitations:"Unknown",quote:""},{id:"finding-002",sourceId:"β-02",question:"Q",summary:"Other",stance:"challenges",locator:"p. 2",methods:"Method B",limitations:"Unknown",quote:""}]};
test("correct finding immutably while preserving exact ID, unrelated evidence and export",()=>{
 const before=JSON.stringify(p);
 const changed=updateClaim(p,"finding-001",{summary:"Corrected <script>inert</script> β",sourceId:"β-02"});
 assert.equal(JSON.stringify(p),before);
 assert.equal(changed.claims.length,2);
 assert.equal(changed.claims[0].id,"finding-001");
 assert.equal(changed.claims[0].methods,"Method A");
 assert.equal(changed.claims[1].summary,"Other");
 assert.equal(changed.claims[0].sourceId,"β-02");
 assert.deepEqual(importProject(exportProject(changed)),changed);
});
test("unknown source, invalid stance and overlength correction fail without mutation",()=>{
 const before=JSON.stringify(p);
 for(const patch of [{sourceId:"unknown"},{stance:"verified"},{summary:"x".repeat(1501)}]){
  assert.throws(()=>updateClaim(p,"finding-001",patch));
  assert.equal(JSON.stringify(p),before);
 }
});
test("changing ID or targeting nonexistent finding is prohibited",()=>{
 assert.throws(()=>updateClaim(p,"finding-001",{id:"other"}),/cannot be changed/);
 assert.throws(()=>updateClaim(p,"missing",{summary:"test"}),/not found/);
});
test("correction recalculates candidate pairs from validated source assignments",()=>{
 const changed=updateClaim(p,"finding-002",{sourceId:"0001"});
 assert.equal(analyzeProject(p).tensionTotal,1);
 assert.equal(analyzeProject(changed).tensionTotal,0);
});
