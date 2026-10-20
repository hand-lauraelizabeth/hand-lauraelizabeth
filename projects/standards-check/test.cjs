#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const html=fs.readFileSync(path.join(__dirname,"index.html"),"utf8");
const script=html.split("<script>")[1]?.split("</script>")[0];
assert.ok(script,"standards check script exists");
const ids=["file","max","cutoff","capacity","csv","analyze","sample","template","reset","message","results","source","metrics","quality","standards","priority","groups","trendNote","trend","changes","matrix","matrixCount","learnerFilter","exportPlan","exportRoster","print"];
const nodes=new Map(ids.map(id=>[id,{value:({max:"4",cutoff:"75",capacity:"4"}[id]||""),innerHTML:"",textContent:"",hidden:id==="results",className:"",listeners:{},addEventListener(t,cb){this.listeners[t]=cb;},click(){return this.listeners.click?.({target:this});},fire(t,target){return this.listeners[t]?.({target});}}]));
let output="";
class BlobMock{constructor(parts){this.parts=parts;this.size=parts.join("").length;output=parts.join("");}}
const context={
 Blob:BlobMock,
 URL:{createObjectURL(){return "blob:test";},revokeObjectURL(){}},
 document:{getElementById(id){assert.ok(nodes.has(id),"unknown DOM id "+id);return nodes.get(id);},createElement(){return {click(){},remove(){}};},body:{appendChild(){}}},
 window:{print(){}},
 setTimeout(fn){fn();},
 console
};
vm.runInNewContext(script,context,{filename:"standards-check-browser.js",timeout:3000});
const $=id=>nodes.get(id);
function importCsv(csv){$("csv").value=csv;$("analyze").click();assert.equal($("message").className,"",String($("message").textContent));}
(async()=>{
 $("sample").click();
 assert.equal($("results").hidden,false);
 assert.match($("source").textContent,/8 learner IDs/);
 assert.match($("metrics").innerHTML,/23\/24/);
 assert.match($("groups").innerHTML,/Collect evidence/);
 assert.match($("trendNote").textContent,/dated/);
 importCsv("learner_id,standard,score,max_score,assessment_date\nA,Reading,3,4,2026-01-01\nA,Reading,4,4,2026-02-01\nB,Reading,5,10,2026-02-01\nC,Reading,,10,2026-02-01\n");
 assert.match($("source").textContent,/long-format/);
 assert.match($("groups").innerHTML,/B \(50%\)/);
 assert.match($("groups").innerHTML,/Collect evidence.*C/s);
 assert.match($("trend").innerHTML,/Scores improved/);
 $("standards").fire("change",{matches:q=>q===".threshold",dataset:{s:"Reading"},value:"50"});
 assert.match($("groups").innerHTML,/No scored learners below/);
 $("learnerFilter").value="B";$("learnerFilter").fire("input",{target:$("learnerFilter")});
 assert.match($("matrixCount").textContent,/1 of 1 matching/);
 assert.doesNotMatch($("matrix").innerHTML,/<th scope="row">A</);
 $("learnerFilter").value="";
 importCsv('learner_id,assessment_date,"Writing, synthesis"\n"<script>alert(1)</script>",2026-01-01,2\n');
 assert.match($("matrix").innerHTML,/&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
 importCsv("learner_id,standard,score,max_score,assessment_date\nA,Reading,3,4,2026-01-01\nA,Reading,1,4,2026-01-01\nB,Reading,999,4,2026-01-01\n");
 assert.match($("quality").innerHTML,/2 row-level import warning/);
 $("csv").value='learner_id,standard,score\nA,"Unfinished,2';
 $("analyze").click();assert.match($("message").textContent,/Unclosed CSV quote/);
 importCsv("learner_id,standard,score,max_score,assessment_date\n=SUM(1+1),Research,1,4,2026-01-01\nB,Research,,4,2026-01-01\n");
 $("groups").fire("input",{matches:q=>q===".teacher-note",dataset:{s:"Research"},value:"Inspect sources and retest"});
 $("exportPlan").click();assert.match(output,/Inspect sources and retest/);
 $("exportRoster").click();assert.match(output,/'=SUM\(1\+1\)/);assert.match(output,/Gather evidence/);
 const file={size:80,text:async()=>("learner_id,Geometry\nL9,4\n")};
 await $("file").fire("change",{files:[file]});
 assert.match($("csv").value,/Geometry/);
 $("analyze").click();assert.match($("source").textContent,/wide-format/);
 $("reset").click();assert.equal($("results").hidden,true);
 console.log("PASS: sample, CSV upload, wide/long imports, normalization, missingness, repeated dates, threshold recalculation, matrix filter, escaping, validation, exports, clear.");
})().catch(e=>{console.error(e);process.exitCode=1;});
