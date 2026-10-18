import {SCHEMA,validateProject,analyzeProject,exportProject,importProject} from "./core.mjs";
let project={schema:SCHEMA,sources:[],claims:[]};
const byId=id=>document.getElementById(id);
function showError(e){byId("error").textContent=e.message;byId("error").focus()}
function showList(id,rows,fn){const ul=byId(id);ul.replaceChildren();for(const row of rows){const li=document.createElement("li");li.textContent=fn(row);ul.append(li)}}
function render(){const a=analyzeProject(project);byId("error").textContent="";byId("counts").textContent=project.sources.length+" sources, "+project.claims.length+" findings, "+a.issues.length+" gaps, "+a.tensions.length+" tensions.";
showList("sources",project.sources,s=>s.id+" — "+s.title);
showList("claims",project.claims,c=>c.id+" — "+c.sourceId+" — "+c.summary+" ("+c.stance+")");
showList("issues",a.issues,x=>x.kind+" — "+(x.claimId||x.sourceId));
showList("tensions",a.tensions,x=>x.question+": "+x.supportClaimId+" / "+x.challengeClaimId+" (user-coded)")}
for(const name of ["source","claim"]){byId(name).addEventListener("submit",event=>{event.preventDefault();const form=event.currentTarget,v=Object.fromEntries(new FormData(form).entries());if(name==="source")v.year=v.year===""?null:Number(v.year);try{project=validateProject({...project,[name==="source"?"sources":"claims"]:[...project[name==="source"?"sources":"claims"],v]});form.reset();render()}catch(e){showError(e)}})}
byId("download").addEventListener("click",()=>{try{const blob=new Blob([exportProject(project)],{type:"application/json"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="literature-evidence-matrix.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(e){showError(e)}});
byId("upload").addEventListener("change",async event=>{const input=event.currentTarget,file=input.files[0];if(!file)return;try{if(file.size>2000000||file.size===0||!file.name.toLowerCase().endsWith(".json"))throw Error("Choose a JSON file up to 2 MB.");const bytes=await file.arrayBuffer();if(bytes.byteLength!==file.size)throw Error("File size changed.");project=importProject(new TextDecoder("utf-8",{fatal:true}).decode(bytes));render()}catch(e){showError(e)}finally{input.value=""}});
render();