import {SCHEMA,validateProject,updateClaim,hasUnsavedClaimChanges,analyzeProject,exportProject,importProject} from "./core.mjs";
let project={schema:SCHEMA,sources:[],claims:[]};
let pendingImport=null, importGeneration=0, editingClaimId=null;
const byId=id=>document.getElementById(id);
function showError(e){byId("error").textContent=e.message;byId("error").focus()}
function clearPreview(){pendingImport=null;byId("import-preview").hidden=true;byId("import-summary").textContent=""}
function invalidateImport(){importGeneration++;clearPreview()}
function status(message){byId("status").textContent=message}
function showList(id,rows,fn){const ul=byId(id);ul.replaceChildren();for(const row of rows){const li=document.createElement("li");li.textContent=fn(row);ul.append(li)}}
function render(){const a=analyzeProject(project);const selector=byId("edit-claim-id");selector.replaceChildren();const placeholder=document.createElement("option");placeholder.value="";placeholder.textContent="Choose a finding";selector.append(placeholder);for(const claim of project.claims){const option=document.createElement("option");option.value=claim.id;option.textContent=claim.id+" — "+claim.sourceId;selector.append(option)}byId("error").textContent="";byId("counts").textContent=project.sources.length+" sources, "+project.claims.length+" findings, "+a.issues.length+" gaps, "+a.tensionTotal+" user-coded candidate pairs"+(a.tensionsOmitted?" (first "+a.tensions.length+" shown; "+a.tensionsOmitted+" additional pairs not displayed).":".");
showList("sources",project.sources,s=>s.id+" — "+s.title);
showList("claims",project.claims,c=>c.id+" — "+c.sourceId+" — "+c.summary+" ("+c.stance+")");
showList("issues",a.issues,x=>x.kind+" — "+(x.claimId||x.sourceId));
showList("tensions",a.tensions,x=>x.question+": "+x.supportClaimId+" / "+x.challengeClaimId+" (user-coded)")}
function hasUnsavedCorrection(){
 return editingClaimId!==null&&hasUnsavedClaimChanges(project,editingClaimId,Object.fromEntries(new FormData(byId("claim")).entries()));
}
function blockUnsavedCorrection(){
 if(!hasUnsavedCorrection())return false;
 showError(Error("Unsaved finding correction: save or cancel it before loading another finding or adding a source."));
 return true;
}
function stopEditing(){editingClaimId=null;const form=byId("claim");form.reset();form.elements.namedItem("id").readOnly=false;byId("claim-submit").textContent="Add finding";byId("cancel-claim-edit").hidden=true}
byId("load-claim").addEventListener("click",()=>{
 const key=byId("edit-claim-id").value,claim=project.claims.find(c=>c.id===key);
 if(!claim){showError(Error("Choose an existing finding to correct."));return}
 if(blockUnsavedCorrection())return;
 editingClaimId=key;const form=byId("claim");
 for(const [field,value] of Object.entries(claim))form.elements.namedItem(field).value=value;
 form.elements.namedItem("id").readOnly=true;
 byId("claim-submit").textContent="Save finding changes";byId("cancel-claim-edit").hidden=false;
 byId("error").textContent="";status("Editing finding "+key+". Its ID is locked. Save or cancel your changes.");
 form.elements.namedItem("summary").focus();
});
byId("cancel-claim-edit").addEventListener("click",()=>{stopEditing();status("Finding correction cancelled. Existing evidence is unchanged.");byId("edit-claim-id").focus()});
for(const name of ["source","claim"]){byId(name).addEventListener("submit",event=>{
 event.preventDefault();if(name==="source"&&blockUnsavedCorrection())return;
 const form=event.currentTarget,v=Object.fromEntries(new FormData(form).entries());
 if(name==="source")v.year=v.year===""?null:Number(v.year);
 try{
  if(name==="claim"&&editingClaimId){
   project=updateClaim(project,editingClaimId,v);
   stopEditing();invalidateImport();render();status("Finding corrected. Exact finding ID and other evidence preserved.");byId("edit-claim-id").focus();
  }else{
   project=validateProject({...project,[name==="source"?"sources":"claims"]:[...project[name==="source"?"sources":"claims"],v]});
   if(name==="source")stopEditing();
   form.reset();invalidateImport();render();status("Entry added. Any pending replacement was cancelled.");
  }
 }catch(e){showError(e)}
})}
byId("download").addEventListener("click",()=>{try{const blob=new Blob([exportProject(project)],{type:"application/json"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="literature-evidence-matrix.json";a.click();status(hasUnsavedCorrection()?"Downloaded saved matrix. One unsaved finding correction was excluded; save it and download again to include it.":"Downloaded saved matrix.");setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(e){showError(e)}});
byId("upload").addEventListener("change",async event=>{
 const input=event.currentTarget,file=input.files[0],generation=++importGeneration;
 clearPreview();status("");byId("error").textContent="";
 if(!file)return;
 try{
  if(file.size>2000000||file.size===0||!file.name.toLowerCase().endsWith(".json"))throw Error("Choose a JSON file up to 2 MB.");
  const bytes=await file.arrayBuffer();
  if(generation!==importGeneration)return;
  if(bytes.byteLength!==file.size)throw Error("File size changed.");
  const candidate=importProject(new TextDecoder("utf-8",{fatal:true}).decode(bytes));
  if(generation!==importGeneration)return;
  pendingImport={candidate,generation};
  byId("import-summary").textContent="Replace the current "+project.sources.length+" sources and "+project.claims.length+" findings with "+candidate.sources.length+" sources and "+candidate.claims.length+" findings? Your current work will be lost unless you downloaded it first."+(hasUnsavedCorrection()?" An unsaved finding correction will also be discarded.":"");
  byId("import-preview").hidden=false;
  byId("confirm-import").focus();
  status("File validated locally. No entries have been replaced.");
 }catch(e){if(generation===importGeneration)showError(e)}
 finally{if(generation===importGeneration)input.value=""}
});
byId("confirm-import").addEventListener("click",()=>{
 if(!pendingImport||pendingImport.generation!==importGeneration){showError(Error("Choose a valid JSON file before confirming."));return}
 stopEditing();project=pendingImport.candidate;invalidateImport();render();status("Import confirmed. The previous matrix was replaced.");
});
byId("cancel-import").addEventListener("click",()=>{invalidateImport();status("Import cancelled. Your current matrix is unchanged.");byId("upload").focus()});
render();