(function(){
"use strict";
// Optional NCES IPEDS 2024–25 HISTORICAL completions index. NOT current programs.
var root=document.getElementById("college-search");
if(!root)return;
var details=root.querySelector("#cs-program-details");
var query=root.querySelector("#cs-program-query");
var results=root.querySelector("#cs-program-options");
var chosen=root.querySelector("#cs-program-chosen");
var choice=root.querySelector("#cs-program-choice");
var remove=root.querySelector("#cs-program-remove");
var level=root.querySelector("#cs-award-level");
var status=root.querySelector("#cs-program-status");
var active=root.querySelector("#cs-program-active");
var retry=root.querySelector("#cs-program-retry");
if(!details||!query||!results||!chosen||!choice||!remove||!level||!status||!active||!retry)return;
var list=[],notify=function(){},ready=false,loading=false,enabled=false;
var selected="",index=new Map(),titles={},keys=[];
var sourceLink="https://nces.ed.gov/ipeds/complete-data-files/C2025_A.zip";
var CIP2020_SHA="6cf0882c1f5beb94981d0a1a72285ab5cf633759f45433fb909afbfb6d6b2657";
var C2025_SHA="555c6522ccf011d54b06520b128badb8558aba3d0038c97f231f5efaa7161183";
var collator=new Intl.Collator("en",{sensitivity:"base"});
function normalize(v){return String(v||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/&/g," and ").replace(/[^a-z0-9]+/g," ").trim().replace(/\s+/g," ");}
var discoveryTerms={}; // editorial terms; no institutional admissions or licensing inference
function wordStart(hay,needle){return hay.split(" ").some(function(w){return w.startsWith(needle);});}
function tokenMatch(hay,needle){var ws=hay.split(" ");return needle.split(" ").every(function(t){return ws.some(function(w){return w.startsWith(t);});});}
function rate(text,key){
 var raw=String(text||"").trim(),q=normalize(raw);
 if(q.length<2)return null;
 var code=q.replace(/^cip /,"").replace(/ /g,"");
 var dot=key.slice(0,2)+"."+key.slice(2);
 var title=normalize(titles[key]),v=discoveryTerms[key]||{},primary=v.aliases||[],related=v.related||[];
 var best=0,origin="";
 function offer(rank,kind){if(rank>best){best=rank;origin=kind;}}
 if(/^\d{2,6}$/.test(code)){
   if(code===key || raw===dot || raw.toUpperCase()==="CIP "+dot)offer(180,"code");
   else if(key.startsWith(code))offer(135,"code");
 }
 if(title===q)offer(160,"title");
 else if(title.startsWith(q))offer(140,"title");
 else if(wordStart(title,q))offer(122,"title");
 else if(title.includes(q))offer(110,"title");
 else if(tokenMatch(title,q))offer(90,"title");
 primary.forEach(function(label){
   var term=normalize(label);
   if(term===q)offer(155,"everyday");
   else if(term.startsWith(q))offer(132,"everyday");
   else if(wordStart(term,q))offer(117,"everyday");
   else if(term.includes(q))offer(100,"everyday");
   else if(tokenMatch(term,q))offer(87,"everyday");
 });
 related.forEach(function(label){
   var term=normalize(label);
   if(term===q)offer(77,"related");
   else if(term.startsWith(q))offer(68,"related");
   else if(term.includes(q)||tokenMatch(term,q))offer(57,"related");
 });
 return best?{cip:key,title:titles[key],score:best,kind:origin}:null;
}
function suggestFor(text,limit){
 var found=[];
 keys.forEach(function(key){var hit=rate(text,key);if(hit)found.push(hit);});
 found.sort(function(a,b){return b.score-a.score||collator.compare(a.title,b.title)||collator.compare(a.cip,b.cip);});
 return {total:found.length,options:found.slice(0,limit||15)};
}
function activeFilters(){return !!(selected||level.value);}
function rows(unitid){return (index.get(unitid)||[]).filter(function(row){
 return (!selected||row[0]===selected)&&(!level.value||row[1]===level.value);
});}
function updateLabel(){
 chosen.hidden=!selected;
 choice.textContent=selected?titles[selected]+" (CIP "+selected+")":"";
 var n=(selected?1:0)+(level.value?1:0);
 active.textContent=n?n+" active historical program "+(n===1?"setting":"settings"):"Optional · historical 2024–25 completions";
}
function clear(){
 selected="";query.value="";level.value="";results.replaceChildren();
 if(ready)status.textContent="Select a field of study, award level, or both to filter reported 2024–25 completions.";
 updateLabel();
}
function setEnabled(yes){
 enabled=!!yes;query.disabled=!enabled||!ready;level.disabled=!enabled||!ready;
}
function suggestions(){
 results.replaceChildren();
 if(!ready)return;
 var typed=query.value.trim();
 if(typed.length<2)return;
 var matches=suggestFor(typed,15),found=matches.total;
 matches.options.forEach(function(hit,i){
  var li=document.createElement("li"),b=document.createElement("button");
  b.type="button";b.className="cs-program-suggestion";
  var name=document.createElement("strong");name.textContent=hit.title;
  var note=document.createElement("span");note.className="cs-program-suggestion-meta";
  note.textContent="CIP "+hit.cip.slice(0,2)+"."+hit.cip.slice(2)+
     (hit.kind==="related"?" · Related subject — compare curricula":
     hit.kind==="everyday"?" · Common-language match":" · Classification match");
  b.append(name,note);
  b.addEventListener("click",function(){
   selected=hit.cip;query.value=hit.title;results.replaceChildren();updateLabel();notify();
  });
  li.appendChild(b);results.appendChild(li);
 });
 status.textContent=found?found.toLocaleString("en-US")+" possible fields, ordered by relevance. Showing "+Math.min(found,15)+". Choose the closest field to filter colleges.":
   "No matching subjects found in the reported 2024–25 programs. Try a broader term, school-major name, or CIP code.";
}
async function verifiedJson(url,expected,signal){
 var res=await fetch(url,{credentials:"omit",signal:signal});
 if(!res.ok)throw Error("Program data request unsuccessful");
 var bytes=await res.arrayBuffer();
 if(!window.crypto||!window.crypto.subtle)throw Error("Secure SHA-256 verification unavailable");
 var hash=await window.crypto.subtle.digest("SHA-256",bytes);
 var result=Array.from(new Uint8Array(hash),function(x){return x.toString(16).padStart(2,"0");}).join("");
 if(result!==expected)throw Error("Program source checksum mismatch");
 return JSON.parse(new TextDecoder().decode(bytes));
}
async function load(){
 if(loading||ready||!enabled||!list.length)return;
 loading=true;retry.hidden=true;status.textContent="Verifying national program data and federal sources…";
 var controller=new AbortController(),timeout=setTimeout(function(){controller.abort();},45000);
 try{
  var base=root.getAttribute("data-program-base");
  if(!base|| !(/^(https:\/\/|\.\/|\.\.\/)/.test(base)) || !base.endsWith("/"))throw Error("Unconfigured program source");
  var r=await fetch(base+"programs.manifest.v1.json",{signal:controller.signal,credentials:"omit"});
  if(!r.ok)throw Error("Program manifest not found");
  var m=await r.json();
  if(m.schema_version!=="1.0"||m.data_kind!=="IPEDS_2024_25_HISTORICAL_FIRST_MAJOR_COMPLETIONS"||
    m.current_program_offering_verified!==false||m.credential_name_institution_verified!==false||
    m.professional_license_eligibility_verified!==false||m.admissions_and_career_matching_authorized!==false||
    m.counts.national_institutions!==6243||m.counts.institutions_with_historical_program_completions!==5658||
    m.counts.joined_program_award_records!==235330||m.counts.distinct_six_digit_cip2020_titles!==2325||
    m.sources.completions.sha256!==C2025_SHA||m.sources.cip2020.sha256!==CIP2020_SHA||
    !Array.isArray(m.shards)||m.shards.length!==13)throw Error("Unexpected historical source manifest");
  var nameMap=await verifiedJson(base+m.cip2020_titles.file,m.cip2020_titles.sha256,controller.signal);
  if(Object.keys(nameMap).length!==2325)throw Error("Wrong classification count");
  Object.keys(nameMap).forEach(function(k){
    if(!/^\d{6}$/.test(k)||typeof nameMap[k]!=="string"||!nameMap[k].trim())
      throw Error("Invalid six-digit CIP classification");
  });
  // Curated synonyms enhance discovery; the federal taxonomy always remains
  // authoritative and the original title/code search works if this file fails.
  var words={};
  try {
    var termResponse=await fetch(base+"program-search-terms.v1.json",{signal:controller.signal,credentials:"omit"});
    if(termResponse.ok){
      var termPayload=await termResponse.json();
      if(termPayload.schema_version==="1.0" &&
         termPayload.official_taxonomy_url==="https://nces.ed.gov/ipeds/cipcode/Files/CIPCode2020.csv" &&
         termPayload.terms_by_cip && !Array.isArray(termPayload.terms_by_cip)){
        Object.entries(termPayload.terms_by_cip).forEach(function(entry){
          var code=entry[0],v=entry[1];
          if(!nameMap[code]||!v||!Array.isArray(v.aliases) ||
            !Array.isArray(v.related||[]) ||
            ![...v.aliases,...(v.related||[])].every(function(t){
              return typeof t==="string"&&t.length>0&&t.length<120;
            }))throw Error("Invalid editorial search term");
          words[code]={aliases:v.aliases,related:v.related||[]};
        });
      }
    }
  }catch(err){words={};}
  var allowed=new Set(list.map(function(x){return x.unitid;}));
  var joined=new Map(),total=0;
  for(var i=0;i<m.shards.length;i+=4){
   var batch=m.shards.slice(i,i+4);
   var parsed=await Promise.all(batch.map(function(f){
     if(!/^programs-\d\d\.json$/.test(f.file)||f.gzip_bytes>768000)throw Error("Invalid program shard");
     return verifiedJson(base+f.file,f.sha256,controller.signal);
   }));
   parsed.forEach(function(payload,j){
     var meta=batch[j],partCount=0;
     if(payload.schema_version!=="1.0"||!Array.isArray(payload.institutions)||
        payload.institutions.length!==meta.institutions)throw Error("Invalid institution shard");
     payload.institutions.forEach(function(entry){
       if(!Array.isArray(entry)||entry.length!==2||!allowed.has(entry[0])||
          !/^\d{6}$/.test(entry[0])||joined.has(entry[0])||
          !Array.isArray(entry[1])||!entry[1].length)throw Error("Invalid UNITID join");
       var found=new Set();
       entry[1].forEach(function(row){
         if(!Array.isArray(row)||row.length!==4||!nameMap[row[0]]||
            !Object.prototype.hasOwnProperty.call(m.award_levels,row[1])||
            !(row[2]===null||(Number.isInteger(row[2])&&row[2]>=0))||
            !["reported","missing_or_suppressed"].includes(row[3])||
            ((row[2]===null)!==(row[3]==="missing_or_suppressed"))||
            found.has(row[0]+"|"+row[1]))throw Error("Invalid CIP6/AWLEVEL row");
         found.add(row[0]+"|"+row[1]);partCount++;
       });
       joined.set(entry[0],entry[1]);
     });
     if(partCount!==meta.program_award_records)throw Error("Program shard count mismatch");
     total+=partCount;
   });
  }
  if(joined.size!==5658||total!==235330)throw Error("Incomplete national program index");
  var observed=new Set();
  joined.forEach(function(rs){rs.forEach(function(r){observed.add(r[0]);});});
  titles=nameMap;index=joined;discoveryTerms=words;
  keys=Array.from(observed).sort(function(a,b){return collator.compare(titles[a],titles[b]);});
  ready=true;setEnabled(true);
  status.textContent="Search everyday words (nurse, coding, HR), subject names, or CIP codes. Choose a suggested field to filter 2024–25 awards. The other 585 institutions lack matched historical evidence—not necessarily current programs.";
  updateLabel();notify();
 }catch(e){
  ready=false;selected="";index=new Map();titles={};keys=[];
  setEnabled(false);level.value="";
  status.textContent="Historical program source could not be independently verified. Other college filters remain available.";
  retry.hidden=false;updateLabel();notify();
 }finally{clearTimeout(timeout);loading=false;}
}
function matches(unitid){return !activeFilters()||!ready||rows(unitid).length>0;}
function getLabels(){
 var out=[];
 if(selected)out.push("Historical field of study: "+titles[selected]+" (CIP "+selected+")");
 if(level.value)out.push("Historical award level: "+level.selectedOptions[0].textContent);
 return out;
}
function cardFor(unitid){
 if(!ready||!activeFilters())return null;
 var match=rows(unitid);if(!match.length)return null;
 var box=document.createElement("div");box.className="cs-card-program";
 var heading=document.createElement("p"),b=document.createElement("strong");
 b.textContent="Reported 2024–25 completions: ";
 heading.append(b,document.createTextNode(match.length+" matching classification/award "+(match.length===1?"row":"rows")));box.appendChild(heading);
 match.slice(0,3).forEach(function(row){
  var p=document.createElement("p");
  var label=level.querySelector('option[value="'+row[1]+'"]');
  p.textContent=titles[row[0]]+" · "+(label?label.textContent:"IPEDS award level "+row[1])+" · "+(row[2]===null?"count unavailable":row[2]+" awards");
  box.appendChild(p);
 });
 var src=document.createElement("a");src.href=sourceLink;src.rel="noopener noreferrer";src.target="_blank";
 src.textContent="NCES IPEDS 2025 completion source";box.appendChild(src);
 return box;
}
details.addEventListener("toggle",function(){if(details.open)load();});
query.addEventListener("input",function(){
 if(selected){selected="";updateLabel();notify();}
 suggestions();
});
query.addEventListener("keydown",function(event){
 if(event.key==="Escape"){results.replaceChildren();return;}
 if(event.key==="ArrowDown"){
  var first=results.querySelector("button");if(first){event.preventDefault();first.focus();}
 }
});
level.addEventListener("change",function(){updateLabel();notify();});
remove.addEventListener("click",function(){selected="";query.value="";results.replaceChildren();updateLabel();notify();query.focus();});
retry.addEventListener("click",load);
window.CollegeProgramSearch=Object.freeze({
 configure:function(institutions,onChange){list=institutions;notify=onChange;setEnabled(true);if(details.open)load();},
 matches:matches,cardFor:cardFor,labels:getLabels,selected:activeFilters,clear:clear,setEnabled:setEnabled,searchSuggestions:suggestFor
});
}());