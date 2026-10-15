// Run: node --test resources/curriculum-lesson-design/tests/syllabus-core.test.cjs
// All examples are synthetic; no student or institutional information.
const test = require("node:test");
const assert = require("node:assert/strict");
const c = require("../syllabus-studio-core.js");
function valid(){
  const d=c.fresh();
  Object.assign(d.meta,{course:"Project reasoning",audience:"Adult learners",resources:"Synthetic scenarios",hoursCap:"4"});
  Object.assign(d.policyChecks,{access:true,integrity:true,late:true,ai:true,grading:true,contact:true});
  d.objectives.push(c.normalizeObjective({text:"Compare two options using explicit criteria."},"O1"),
    c.normalizeObjective({text:"Justify a decision using evidence."},"O2"));
  d.sessions.push(c.normalizeSession({week:"Week 1",topic:"Criteria",activity:"Compare examples",
    hours:2,objectiveIds:["O1"]},"S1"));
  d.sessions.push(c.normalizeSession({week:"Week 2",topic:"Reasoned decision",activity:"Independent decision memo",
    hours:2,objectiveIds:["O1","O2"]},"S2"));
  d.assessments.push(c.normalizeAssessment({title:"Practice",type:"Formative",week:"Week 1",
    weight:null,evidence:"Criteria checklist",feedback:"Peer feedback",objectiveIds:["O1"]},"A1"));
  d.assessments.push(c.normalizeAssessment({title:"Memo",type:"Graded",week:"Week 2",weight:100,
    evidence:"Supported conclusion",feedback:"Rubric with revision",objectiveIds:["O1","O2"]},"A2"));
  return d;
}
test("empty plan has stable schema",()=>{const x=c.fresh();assert.equal(x.kind,c.KIND);
  assert.deepEqual(x.objectives,[]);assert.deepEqual(x.policyChecks,{});});
test("basic plan yields complete assessment alignment",()=>{
  const x=c.review(valid());assert.equal(x.objectives,2);assert.equal(x.aligned,2);
  assert.equal(x.gradedWeightTotal,100);assert.equal(x.formativeCount,1);});
test("gaps not confused with full compliance",()=>{
  assert.ok(c.review(valid()).flags.length===0);
  const x=valid(); x.policyChecks.access=false;
  assert.ok(c.review(x).flags.some(f=>f.type==="policy"&&/accessibility/i.test(f.message)));
});
test("missing practice detected",()=>{
  const x=valid();x.sessions[0].activity="";x.sessions[1].objectiveIds=["O2"];
  assert.ok(c.review(x).flags.some(f=>f.message.includes("O1 has no described instructional activity")));
});
test("missing objective assessment detected",()=>{
  const x=valid();x.assessments.forEach(a=>a.objectiveIds=["O1"]);
  assert.ok(c.review(x).flags.some(f=>f.message.includes("O2 has no linked assessment")));
});
test("missing assessment evidence detected",()=>{
  const x=valid();x.assessments[1].evidence="";
  assert.ok(c.review(x).flags.some(f=>f.message.includes("A2 needs evidence")));
});
test("graded total accounts only for graded entries",()=>{
  const x=valid();x.assessments[1].weight=80;
  assert.equal(c.review(x).gradedWeightTotal,80);
  assert.ok(c.review(x).flags.some(f=>f.type==="grade"&&/80/.test(f.message)));
});
test("missing grade weight flagged",()=>{
  const x=valid();x.assessments[1].weight=null;
  assert.ok(c.review(x).flags.some(f=>f.type==="grade"&&/needs a grading weight/.test(f.message)));
});
test("formative nonzero grade weight rejected",()=>{
  const x=valid();x.assessments[0].weight=20;
  assert.throws(()=>c.validate(x),/Formative/);
});
test("zero formative weight allowed",()=>{
  const x=valid();x.assessments[0].weight=0;
  assert.equal(c.validate(x).assessments[0].weight,0);
});
test("float weights summed precisely",()=>{
  const x=valid();x.assessments[1].weight=33.33;
  x.assessments.push(c.normalizeAssessment({title:"Second",type:"Graded",weight:66.67,
  evidence:"Essay",feedback:"Comments",objectiveIds:["O1"]},"A3"));
  assert.equal(c.review(x).gradedWeightTotal,100);
});
test("workload checks sum repeated week labels, not averages",()=>{
  const x=valid();x.sessions[1].week="Week 1";x.sessions[1].hours=3;
  assert.ok(c.review(x).flags.some(f=>/Week 1 has 5/.test(f.message)));
});
test("blank hours distinct from zero",()=>{
  const x=valid();x.sessions[0].hours="";
  assert.equal(c.validate(x).sessions[0].hours,null);
  x.sessions[0].hours=0;assert.equal(c.validate(x).sessions[0].hours,0);
});
test("invalid workload numbers rejected",()=>{
  for(const v of [-1,170,"invalid",Infinity]){const x=valid();x.sessions[0].hours=v;
    assert.throws(()=>c.validate(x),/Invalid preparation hours/);}
});
test("duplicate and dangling identifiers rejected",()=>{
  let x=valid();x.sessions[1].id="S1";assert.throws(()=>c.validate(x),/Duplicate/);
  x=valid();x.assessments[0].objectiveIds=["O999"];assert.throws(()=>c.validate(x),/does not exist/);
});
test("invalid unsupported import rejected",()=>assert.throws(()=>c.validate({kind:"unknown"}),/Unsupported/));
test("100 items is accepted; 101 refused",()=>{
  const x=valid();x.objectives=[];
  for(let i=1;i<=100;i++)x.objectives.push(c.normalizeObjective({text:"Outcome "+i},"O"+i));
  assert.equal(c.validate(x).objectives.length,100);
  x.objectives.push(c.normalizeObjective({text:"Overflow"},"O101"));
  assert.throws(()=>c.validate(x),/Maximum 100/);
});
test("Canvas v1 import preserves objective text and session mapping",()=>{
  const src={format:"leh-curriculum-canvas",version:1,fields:{title:"Community teaching",
  audience:"Mixed experience learners",task:"Communicate a decision",format:"Live",access:"Readable alternatives",
  feedback:"Feedback before submission"},objectives:[
    {sentence:"Learners will formulate a clear inquiry."},
    {sentence:"Learners will critique a written response."}
  ],modules:[{name:"Practice",target:"2",activity:"Review examples",evidence:"Critique memo"},
    {name:"Transfer",target:"1",activity:"Write in a new scenario",evidence:"Draft request"}]};
  const x=c.fromCanvas(src);
  assert.equal(x.objectives[0].text,"Learners will formulate a clear inquiry.");
  assert.deepEqual(x.sessions[0].objectiveIds,["O2"]);
  assert.deepEqual(x.assessments[1].objectiveIds,["O1"]);
  assert.ok(x.assessments.every(a=>a.type==="Formative"&&a.weight===null));
  assert.ok(x.meta.resources.includes("Readable alternatives"));
  assert.ok(!x.meta.policies);
});
test("Canvas import refuses future or invalid schemas",()=>{
  assert.throws(()=>c.fromCanvas({format:"leh-curriculum-canvas",version:2,fields:{},objectives:[],modules:[]}),/Not an exported/);
});
test("JSON export/reload works without blank-to-zero coercion",()=>{
 const x=c.validate(JSON.parse(JSON.stringify(valid())));
 assert.equal(x.assessments[0].weight,null);
 assert.equal(x.sessions[0].hours,2);
});
test("syllabus explicitly avoids invented institutional policies",()=>{
 const x=valid();x.meta.policies="";
 const text=c.syllabusText(x);
 assert.match(text,/Institutional policies not supplied/);
 assert.match(text,/METHOD NOTE/);
});
test("source text stays unmodified in readable export",()=>{
 const x=valid();x.meta.course="Research & Methods";
 assert.ok(c.syllabusText(x).includes("Research & Methods"));
});
test("generated IDs use next unused identity",()=>{
 assert.equal(c.identifier("O",valid().objectives),"O3");
});
