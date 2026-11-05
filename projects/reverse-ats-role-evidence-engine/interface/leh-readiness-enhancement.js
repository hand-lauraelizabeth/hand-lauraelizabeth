(function(){
"use strict";

function make(d,tag,cls,text){var x=d.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=text;return x;}
function install(){
 try{
 var d=document;
 if(!d||!d.getElementById("candidate")||!d.getElementById("career-workbench")||d.getElementById("leh-readiness"))return;
 var css=d.createElement("style");css.textContent="#leh-readiness{margin:18px 0;background:#fff;border:2px solid #bfd3c7;border-radius:15px;padding:20px}#leh-readiness h2{margin:0 0 6px;color:#17382e}#leh-readiness .leh-sub{color:#4d6056;font-size:14px}#leh-readiness .leh-actions{display:flex;flex-wrap:wrap;gap:9px;margin:14px 0}#leh-readiness button{border:1px solid #255d49;background:#255d49;color:#fff;border-radius:9px;padding:10px 14px;font-size:14px;font-weight:700;min-height:44px;cursor:pointer}#leh-readiness button.leh-secondary{background:#fff;color:#255d49}#leh-readiness button:focus-visible{outline:3px solid #99bca7;outline-offset:3px}#leh-readiness .leh-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin-top:12px}#leh-readiness .leh-check{background:#f5f8f5;border:1px solid #d4dfd6;border-radius:10px;padding:12px}#leh-readiness .leh-check strong{display:block;margin-bottom:4px}#leh-readiness .leh-check span{font-size:13px;color:#465a50}#leh-readiness .leh-plan{background:#eef4ef;border-left:4px solid #35644d;border-radius:6px;padding:12px 14px;margin-top:14px}#leh-readiness .leh-plan ol{margin:8px 0 0;padding-left:22px}#leh-readiness a{color:#1c5440;text-decoration:underline}#leh-readiness .leh-status{font-size:13px;color:#4b5d52;min-height:20px}";
 d.head.appendChild(css);
 var sec=make(d,"section","panel");sec.id="leh-readiness";sec.setAttribute("aria-labelledby","leh-readiness-title");
 var h=make(d,"h2","","Quick résumé readiness review");h.id="leh-readiness-title";sec.appendChild(h);
 sec.appendChild(make(d,"p","leh-sub","Uses your résumé and optional posting to flag visible evidence and practical revisions. No employer ATS score, eligibility decision, or invented experience."));
 var actionsBar=make(d,"div","leh-actions");
 var run=make(d,"button","","Check résumé readiness");run.type="button";actionsBar.appendChild(run);
 var draft=make(d,"button","leh-secondary","Build targeted résumé draft");draft.type="button";actionsBar.appendChild(draft);
 var copy=make(d,"button","leh-secondary","Copy revision plan");copy.type="button";copy.disabled=true;actionsBar.appendChild(copy);sec.appendChild(actionsBar);
 var status=make(d,"p","leh-status","Paste your résumé in the first panel above, then run this review.");status.setAttribute("role","status");status.setAttribute("aria-live","polite");sec.appendChild(status);
 var out=make(d,"div","");sec.appendChild(out);
 var sources=make(d,"p","leh-sub","Reference: ");var onet=make(d,"a","","O*NET occupations");onet.href="https://www.onetonline.org/";onet.target="_blank";onet.rel="noopener noreferrer";sources.appendChild(onet);sources.appendChild(d.createTextNode(" · "));var bls=make(d,"a","","BLS regional wages");bls.href="https://www.bls.gov/oes/current/oessrcma.htm";bls.target="_blank";bls.rel="noopener noreferrer";sources.appendChild(bls);sec.appendChild(sources);
 var work=d.getElementById("career-workbench");work.parentNode.insertBefore(sec,work);
 var lastPlan="";
 function check(g,name,result,note){var c=make(d,"div","leh-check");c.appendChild(make(d,"strong","",name+": "+result));c.appendChild(make(d,"span","",note));g.appendChild(c);}
 function review(){
  var text=d.getElementById("candidate").value.trim();var job=(d.getElementById("job")||{}).value||"";var zip=(d.getElementById("career-zip")||{}).value||"";
  out.replaceChildren();copy.disabled=true;lastPlan="";
  if(text.length<80){status.textContent="Add a résumé or evidence summary of at least 80 characters first.";return;}
  var headings=/(^|\n)\s*(professional\s+)?(experience|employment|education|skills|projects|certifications|awards|summary|profile)\s*:?(\n|$)/im.test(text);
  var years=/\b(?:19|20)\d{2}\b/.test(text);
  var metrics=/(?:\d+(?:\.\d+)?\s?%|\$\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*\s?(?:students|learners|employees|projects|workshops|participants|clients|reports|records|courses)\b)/i.test(text);
  var bullets=/(^|\n)\s*(?:[-•*]|\d+\.)\s+\S/m.test(text);
  var vague=/\b(responsible for|helped with|various tasks|worked on|involved in)\b/i.test(text);
  var g=make(d,"div","leh-grid");out.appendChild(g);
  check(g,"Sections",headings?"Visible":"Review","Use accurate, clearly labeled Experience, Education, and Skills sections.");
  check(g,"Dates",years?"Year detected":"Review","Check each employer, role, and date; a detected year does not establish accuracy.");
  check(g,"Outcomes",metrics?"Quantities visible":"Review","Where evidence supports them, describe scale and results without inventing numbers.");
  check(g,"Bullets",bullets?"Detected":"Review","Use clear, specific bullets for contributions under each role.");
  check(g,"Clarity",vague?"Vague phrasing detected":"No common flags","Replace generic wording with verifiable actions and scope.");
  var plan=[];
  if(!headings)plan.push("Add conventional, descriptive section headings.");
  if(!years)plan.push("Confirm the dates for each role, project, and degree.");
  if(!bullets)plan.push("Turn role descriptions into concise evidence-based bullets.");
  if(!metrics)plan.push("Add documented numbers, scale, or results where you have them.");
  if(vague)plan.push("Replace vague phrases with concrete contributions.");
  if(job.trim()){
   var stop=new Set("this that with from these those their there your which about using experience years skills ability must should required preferred qualification responsibilities position candidates work team role strong excellent ability related including across within management development support".split(" "));
   var counts=new Map();(job.toLowerCase().match(/[a-z][a-z-]{3,}/g)||[]).forEach(function(w){if(!stop.has(w))counts.set(w,(counts.get(w)||0)+1);});
   var absent=[...counts.entries()].sort(function(a,b){return b[1]-a[1];}).map(function(x){return x[0];}).filter(function(w){return text.toLowerCase().indexOf(w)===-1;}).slice(0,6);
   if(absent.length)plan.push("Review these recurring posting words against your actual experience (do not force unsupported terms): "+absent.join(", ")+".");
   plan.push("Run the Reverse ATS audit below to inspect required versus preferred criteria and unresolved evidence.");
  }else{plan.push("Paste a complete job posting when you need a targeted gap review.");}
  if(zip&&!/^\d{5}$/.test(zip))plan.push("Use a valid five-digit U.S. ZIP for wage lookup.");
  if(/^\d{5}$/.test(zip))plan.push("Compare regional BLS wage percentiles for O*NET-matched occupations; a ZIP maps to a broader labor market.");
  plan.push("Generate a targeted résumé draft and confirm all dates, employers, claims, and metrics before sharing.");
  var block=make(d,"div","leh-plan");block.appendChild(make(d,"strong","","Next edits (not an ATS score)"));var list=make(d,"ol");plan.forEach(function(item){list.appendChild(make(d,"li","",item));});block.appendChild(list);out.appendChild(block);
  lastPlan="RÉSUMÉ READINESS — REVISION PLAN\n\n"+plan.map(function(x,i){return (i+1)+". "+x;}).join("\n")+"\n\nBased only on supplied text. This is not an employer score or salary offer.";
  copy.disabled=false;status.textContent="Review complete: "+plan.length+" concrete edits suggested. This review did not upload your résumé.";
 }
 run.addEventListener("click",review);
 draft.addEventListener("click",function(){if(d.getElementById("candidate").value.trim().length<80){status.textContent="Paste your résumé above before building a draft.";return;}var b=d.getElementById("resume-build");if(b){b.click();d.getElementById("resume-workbench").scrollIntoView({behavior:"smooth",block:"start"});}});
 copy.addEventListener("click",async function(){if(!lastPlan)return;try{await navigator.clipboard.writeText(lastPlan);status.textContent="Revision plan copied.";}catch(e){status.textContent="Copy unavailable in this browser; select the on-screen list to copy it manually.";}});
 function augmentOnet(){
  var result=d.getElementById("career-results");if(!result)return;
  result.querySelectorAll(".career-card").forEach(function(c){if(c.querySelector('a[href*="onetonline.org/link/"]')||c.querySelector(".leh-onet-direct"))return;var match=(c.textContent||"").match(/\b\d{2}-\d{4}\.\d{2}\b/);if(!match)return;var a=make(d,"a","leh-onet-direct","Open matching O*NET occupation");a.href="https://www.onetonline.org/link/summary/"+match[0];a.target="_blank";a.rel="noopener noreferrer";a.style.display="inline-block";a.style.marginTop="8px";c.appendChild(a);});
 }
 var result=d.getElementById("career-results");if(result){new MutationObserver(augmentOnet).observe(result,{childList:true});augmentOnet();}
 }catch(err){/* Preserve the original tools if the optional enhancement cannot mount. */}
}
install();
})();