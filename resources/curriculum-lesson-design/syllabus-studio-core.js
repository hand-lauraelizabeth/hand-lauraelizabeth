/* Syllabus & Assessment Alignment Builder — client-side, no network calls.
   Independent educational planning resource by Laura Elizabeth Hand. */
(function (host, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (host) host.LEHSyllabusCore = api;
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";
  const KIND = "leh-syllabus-studio", MAX_ITEMS = 100;
  const META_FIELDS = ["course","code","term","audience","description","format","resources","instructor","contact","policies","hoursCap","scheduleNotes"];
  const POLICY_CHECKS = [
    ["access","Accessibility and accommodations: verify official institutional language"],
    ["integrity","Academic integrity and collaboration expectations"],
    ["late","Late and make-up work expectations"],
    ["ai","AI-assisted work permissions and documentation"],
    ["grading","Grading and reassessment expectations"],
    ["contact","Communication channels and response expectations"]
  ];
  const str = (x, max=5000) => String(x ?? "").slice(0,max).trim();
  const num = x => (x === "" || x === null || typeof x === "undefined") ? null :
    (typeof x === "number" || (typeof x === "string" && x.trim()!=="" && Number.isFinite(Number(x)))) ? Number(x) : NaN;
  function fresh() { return {kind:KIND,version:1,meta:Object.fromEntries(META_FIELDS.map(k=>[k,""])),objectives:[],sessions:[],assessments:[]}; }
  function identifier(prefix, data) {
    const used = new Set(data.map(x=>x.id));
    let i=1; while(used.has(prefix+i)) i++;
    return prefix+i;
  }
  function uniqueIds(xs) {
    return [...new Set(Array.isArray(xs) ? xs.filter(x=>typeof x==="string" && x) : [])];
  }
  function normalizeObjective(o,id) {
    return {id:str(o.id||id,40),text:str(o.text||o.sentence||o.label,1500),source:str(o.source||"authored",80)};
  }
  function normalizeSession(s,id) {
    return {id:str(s.id||id,40),week:str(s.week,80),topic:str(s.topic,250),activity:str(s.activity,1500),
      reading:str(s.reading,1500),hours:num(s.hours),objectiveIds:uniqueIds(s.objectiveIds)};
  }
  function normalizeAssessment(a,id) {
    return {id:str(a.id||id,40),title:str(a.title,250),type:a.type==="Formative"?"Formative":"Graded",
      week:str(a.week,80),weight:num(a.weight),evidence:str(a.evidence,1500),feedback:str(a.feedback,1500),
      objectiveIds:uniqueIds(a.objectiveIds)};
  }
  function validate(state) {
    if (!state || state.kind !== KIND || state.version!==1 || !state.meta ||
      !Array.isArray(state.objectives) || !Array.isArray(state.sessions) || !Array.isArray(state.assessments)) {
      throw new Error("Unsupported syllabus plan format.");
    }
    const sections=["objectives","sessions","assessments"];
    sections.forEach(k=>{if(state[k].length>MAX_ITEMS)throw new Error("Maximum "+MAX_ITEMS+" "+k+" per plan.");});
    const clean=fresh();
    META_FIELDS.forEach(k=>clean.meta[k]=str(state.meta[k],5000));
    clean.objectives=state.objectives.map((o,i)=>normalizeObjective(o,"O"+(i+1)));
    clean.sessions=state.sessions.map((o,i)=>normalizeSession(o,"S"+(i+1)));
    clean.assessments=state.assessments.map((o,i)=>normalizeAssessment(o,"A"+(i+1)));
    for(const key of sections) {
      const ids=clean[key].map(x=>x.id);
      if(new Set(ids).size!==ids.length||ids.some(x=>!x||!(/^[A-Za-z][A-Za-z0-9_-]{0,39}$/.test(x)))) {
        throw new Error("Duplicate or invalid "+key+" identifiers.");
      }
    }
    const validObjectives=new Set(clean.objectives.map(x=>x.id));
    [...clean.sessions,...clean.assessments].forEach(entry=>{
      if(entry.objectiveIds.some(id=>!validObjectives.has(id)))throw new Error("A mapped objective does not exist: "+entry.id);
    });
    clean.sessions.forEach(s=>{if(s.hours!==null&&(!Number.isFinite(s.hours)||s.hours<0||s.hours>168))
      throw new Error("Invalid preparation hours for "+s.id);});
    clean.assessments.forEach(a=>{
      if(a.weight!==null&&(!Number.isFinite(a.weight)||a.weight<0||a.weight>100))throw new Error("Invalid grading weight for "+a.id);
      if(a.type==="Formative"&&a.weight!==null&&a.weight!==0)throw new Error("Formative assessments cannot carry a grading weight.");
    });
    return clean;
  }
  function fromCanvas(raw) {
    if(!raw || raw.format!=="leh-curriculum-canvas" || raw.version!==1 ||
       !raw.fields || !Array.isArray(raw.objectives) || !Array.isArray(raw.modules))
      throw new Error("Not an exported Curriculum Planning Canvas (version 1).");
    if(raw.objectives.length>MAX_ITEMS||raw.modules.length>MAX_ITEMS)throw new Error("Canvas contains too many entries.");
    const data=fresh(), f=raw.fields;
    data.meta.course=str(f.title);data.meta.audience=str(f.audience);
    data.meta.description=str(f.task); data.meta.format=str(f.format);
    data.meta.resources=str(f.access ? "Access considerations: "+f.access : "");
    data.objectives=raw.objectives.map((o,i)=>normalizeObjective({text:o.sentence||["Learners will be able to",o.verb,o.knowledge].join(" "),source:"curriculum-canvas"},"O"+(i+1)));
    data.sessions=raw.modules.map((m,i)=>{
      const mapped=Number(m.target);
      const objectiveIds=Number.isInteger(mapped)&&mapped>=1&&mapped<=data.objectives.length?["O"+mapped]:[];
      return normalizeSession({id:"S"+(i+1),week:"Session "+(i+1),topic:m.name,
        activity:m.activity,reading:"",hours:null,objectiveIds},"S"+(i+1));
    });
    // The canvas has practice/assessment evidence per module, but not graded work.
    // Preserve that evidence as ungraded formative records without inventing grading percentages.
    raw.modules.forEach((m,i)=>{
      if(!str(m.evidence))return;
      const target=data.sessions[i].objectiveIds;
      data.assessments.push(normalizeAssessment({id:"A"+(data.assessments.length+1),
        title:str(m.name)||"Session "+(i+1),type:"Formative",week:"Session "+(i+1),weight:null,
        evidence:m.evidence,feedback:str(f.feedback),objectiveIds:target},"A"+(data.assessments.length+1)));
    });
    data.meta.scheduleNotes="Imported from Curriculum Planning Canvas. Verify all dates, requirements, assignments, and institution-specific policies before using with students.";
    return validate(data);
  }
  function alignment(state) {
    const d=validate(state), result=[];
    for(const o of d.objectives) {
      const sessions=d.sessions.filter(s=>s.objectiveIds.includes(o.id));
      const assessments=d.assessments.filter(a=>a.objectiveIds.includes(o.id));
      result.push({id:o.id,objective:o.text,sessions:sessions.map(s=>s.id),
        assessments:assessments.map(a=>a.id),
        practice:sessions.some(s=>!!s.activity),
        evidence:assessments.some(a=>!!a.evidence)});
    }
    return result;
  }
  function review(state) {
    const d=validate(state), flags=[];
    function flag(type,message){flags.push({type,message});}
    if(!d.meta.course)flag("missing","Add the course or workshop title.");
    if(!d.meta.audience)flag("missing","Describe learners and starting conditions.");
    if(!d.objectives.length)flag("missing","Add at least one measurable learning objective.");
    if(!d.sessions.length)flag("missing","Add the course or session sequence.");
    if(!d.assessments.length)flag("missing","Add assessment evidence.");
    const map=alignment(d);
    map.forEach(m=>{
      if(!m.sessions.length)flag("alignment",m.id+" has no linked session or practice.");
      if(!m.practice)flag("alignment",m.id+" has no described instructional activity.");
      if(!m.assessments.length)flag("alignment",m.id+" has no linked assessment.");
      if(!m.evidence)flag("alignment",m.id+" has no described assessment evidence.");
    });
    d.sessions.forEach(s=>{
      if(!s.objectiveIds.length)flag("alignment",s.id+" has no mapped objective.");
      if(!s.topic)flag("missing",s.id+" needs a topic.");
      if(!s.activity)flag("missing",s.id+" needs a learning activity.");
    });
    d.assessments.forEach(a=>{
      if(!a.objectiveIds.length)flag("alignment",a.id+" has no mapped objective.");
      if(!a.evidence)flag("missing",a.id+" needs evidence/assessment criteria.");
      if(!a.feedback)flag("review",a.id+" needs a feedback or review plan.");
      if(a.type==="Graded"&&a.weight===null)flag("grade",a.id+" needs a grading weight.");
      if(a.type==="Formative"&&a.weight===null){} // expected: no grade
    });
    const graded=d.assessments.filter(a=>a.type==="Graded");
    const allWeighted=graded.every(a=>a.weight!==null);
    const sum=graded.reduce((n,a)=>n+(a.weight||0),0);
    if(graded.length && allWeighted && Math.abs(sum-100)>0.001)
      flag("grade","Grading weights total "+round(sum)+"%, not 100%.");
    if(!graded.length)flag("review","No graded assessments. Confirm whether this is an intentionally ungraded learning experience.");
    const cap=num(d.meta.hoursCap);
    if(cap!==null) {
      if(!Number.isFinite(cap)||cap<=0||cap>168)flag("workload","Enter a realistic positive hours-per-week threshold, or leave it blank.");
      else {
        const weeks=new Map();
        d.sessions.forEach(s=>{if(s.week&&s.hours!==null)weeks.set(s.week,(weeks.get(s.week)||0)+s.hours)});
        weeks.forEach((hours,week)=>{if(hours>cap)flag("workload",week+" has "+round(hours)+" estimated independent-work hours (threshold "+round(cap)+").");});
      }
    }
    POLICY_CHECKS.forEach(([key,title])=>{
      if(!d.meta.policies.toLowerCase().includes("["+key+"]"))flag("policy",title+" — include or verify locally applicable language.");
    });
    if(!d.meta.resources)flag("review","List required and optional learning resources and access alternatives.");
    return {flags,gradedWeightTotal:round(sum),gradedCount:graded.length,formativeCount:d.assessments.length-graded.length,
      objectives:d.objectives.length,aligned:map.filter(m=>m.practice&&m.evidence).length,matrix:map};
  }
  function round(x){return Math.round(x*100)/100;}
  function syllabusText(state) {
    const d=validate(state),a=[],add=(...x)=>a.push(...x);
    add("COURSE PLAN / DRAFT SYLLABUS",d.meta.course||"[Course title required]",d.meta.code?("Course code: "+d.meta.code):"",d.meta.term?("Term: "+d.meta.term):"");
    add("","PURPOSE & LEARNERS",d.meta.description||"[Course purpose not entered]",d.meta.audience||"[Learner context not entered]");
    add("","FORMAT & CONTACT",d.meta.format||"[Delivery format not entered]",d.meta.instructor||"[Instructor / facilitator not entered]",d.meta.contact||"[Contact and availability not entered]");
    add("","LEARNING OUTCOMES");
    d.objectives.forEach(o=>add(o.id+". "+o.text));
    add("","EVALUATION & ASSESSMENT");
    d.assessments.forEach(x=>add(x.title+" ["+x.type+"]"+(x.weight!==null?" — "+x.weight+"%":""),"Timing: "+(x.week||"Not scheduled"),"Evidence: "+(x.evidence||"Not specified"),"Feedback: "+(x.feedback||"Not specified"),"Aligned outcomes: "+(x.objectiveIds.join(", ")||"Not mapped")));
    add("","WEEKLY / SESSION OUTLINE");
    d.sessions.forEach(x=>add((x.week||"Unscheduled")+" — "+(x.topic||"Untitled session"),"Practice: "+(x.activity||"Not specified"),"Resources: "+(x.reading||"Not specified"),"Aligned outcomes: "+(x.objectiveIds.join(", ")||"Not mapped"),"Estimated independent work: "+(x.hours===null?"Not estimated":x.hours+" hours")));
    add("","LEARNING MATERIALS & ACCESS",d.meta.resources||"[Materials and alternatives not entered]");
    add("","POLICIES — REVIEW AGAINST YOUR INSTITUTION",d.meta.policies||"[Institutional policies not supplied. Do not assume a generic sample meets institutional requirements.]");
    add("","SCHEDULE NOTES",d.meta.scheduleNotes||"[No additional notes]");
    add("","METHOD NOTE","Planning draft generated locally. Verify institutional policies, actual dates, grade calculations, disciplinary assessment validity, accessibility, and resource availability before distribution.");
    return a.filter((v,i)=>v!==""||a[i-1]!=="").join("\n");
  }
  return {KIND, fresh, validate, fromCanvas, alignment, review, syllabusText, identifier,normalizeObjective,normalizeSession,normalizeAssessment};
});