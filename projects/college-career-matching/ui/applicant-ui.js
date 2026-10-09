/* Progressive enhancement for applicant planning; synthetic demo remains the fallback. */
(function(){
  "use strict";
  const M=window.MatcherSignals;
  if(!M)return;
  const panel=document.createElement("fieldset");
  panel.setAttribute("aria-label","Applicant and school size preferences");
  panel.innerHTML='<legend>Applicant context and school size</legend>'+
    '<label for="gpaValue">GPA (optional)</label><input id="gpaValue" type="number" min="0" step=".01" placeholder="Unknown / omit">'+
    '<label for="gpaScale">GPA scale</label><select id="gpaScale"><option value="4">4.0</option><option value="5">5.0</option><option value="100">100</option></select>'+
    '<label for="gpaWeight">GPA weighting</label><select id="gpaWeight"><option value="unweighted">Unweighted</option><option value="weighted">Weighted</option></select>'+
    '<label for="testingChoice">Testing information</label><select id="testingChoice"><option value="omit">No score / unknown</option><option value="test_optional">Prefer test-optional</option><option value="test_blind">Prefer test-blind</option><option value="sat">SAT total</option><option value="act">ACT composite</option></select>'+
    '<label for="satTotal">SAT total (400–1600)</label><input id="satTotal" type="number" min="400" max="1600" placeholder="Optional">'+
    '<label for="actComposite">ACT composite (1–36)</label><input id="actComposite" type="number" min="1" max="36" placeholder="Optional">'+
    '<fieldset id="satSections"><legend>SAT sections (optional)</legend>' +
    '<label for="satReadingWriting">Reading and Writing (200–800)</label><input id="satReadingWriting" type="number" min="200" max="800" step="10">' +
    '<label for="satMath">Math (200–800)</label><input id="satMath" type="number" min="200" max="800" step="10"></fieldset>' +
    '<fieldset id="actSections"><legend>ACT sections (optional)</legend>' +
    '<label for="actEnglish">English (1–36)</label><input id="actEnglish" type="number" min="1" max="36">' +
    '<label for="actMath">Math (1–36)</label><input id="actMath" type="number" min="1" max="36">' +
    '<label for="actReading">Reading (1–36)</label><input id="actReading" type="number" min="1" max="36">' +
    '<label for="actScience">Science (1–36; optional)</label><input id="actScience" type="number" min="1" max="36"></fieldset>' +
    '<label for="sizeKind">Enrollment definition</label><select id="sizeKind"><option value="any">No school-size preference</option><option value="undergraduate">Undergraduate enrollment</option><option value="total">Total enrollment</option></select>'+
    '<label for="sizeMin">Minimum students</label><input id="sizeMin" type="number" min="0" placeholder="No minimum">'+
    '<label for="sizeMax">Maximum students</label><input id="sizeMax" type="number" min="0" placeholder="No maximum">'+
    '<p id="applicantFeedback" class="meta" role="status" aria-live="polite"></p>'+
    '<p class="meta">GPA and test scores are planning context, not admission predictions. Enrollment filters exclude unknown counts when active; no enrollment data is invented. Verify current test policy and reporting year directly.</p>';
  const aside=document.querySelector("aside.card");
  if(!aside)return;
  aside.append(panel);
  const get=id=>document.getElementById(id);
  const originalScore=window.score;
  window.score=function(record){
    const kind=get("sizeKind").value;
    const min=get("sizeMin").value===""?null:Number(get("sizeMin").value);
    const max=get("sizeMax").value===""?null:Number(get("sizeMax").value);
    if(min!==null&&(!Number.isInteger(min)||min<0)||max!==null&&(!Number.isInteger(max)||max<0)||min!==null&&max!==null&&min>max)return null;
    if(!M.sizeMatch(record,kind,min,max).include)return null;
    return originalScore(record);
  };
  const baseRender=window.render;
  window.render=function(){
    const g=M.validateGpa(get("gpaValue").value,get("gpaScale").value,get("gpaWeight").value);
    const t=M.validateTesting(get("testingChoice").value,get("satTotal").value,get("actComposite").value);
    const bad=g.ok?(t.ok?"":t.reason):g.reason;
    get("applicantFeedback").textContent=bad||"Applicant inputs do not determine admission odds.";
    baseRender();
    if(bad)get("applicantFeedback").textContent=bad+" Correct this input before using it for planning.";
  };
  panel.querySelectorAll("input,select").forEach(el=>el.addEventListener("input",()=>window.render()));
  window.render();
})();
