import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {SCHEMA} from "./core.mjs";

const nodes=new Map();
let focused="";
function node(id){
 if(!nodes.has(id))nodes.set(id,{
  id,textContent:"",hidden:id==="import-preview",value:"",files:[],fields:[],items:[],
  elements:{namedItem(){return {value:"",readOnly:false,focus(){}}}},
  listeners:{},addEventListener(name,fn){this.listeners[name]=fn},
  focus(){focused=id},reset(){this.fields=[]},replaceChildren(){this.items=[]},
  append(item){this.items.push(item)}
 });
 return nodes.get(id);
}
globalThis.document={
 getElementById:node,
 createElement(tag){return {tag,textContent:"",click(){}}}
};
globalThis.FormData=class{constructor(form){this.form=form}entries(){return this.form.fields}};
await import("./app.mjs");
async function emit(id,type,extra={}){
 const el=node(id),fn=el.listeners[type];
 assert.equal(typeof fn,"function",id+" "+type+" listener");
 return await fn({currentTarget:el,preventDefault(){},...extra});
}
function fileFor(json,options={}){
 const bytes=new TextEncoder().encode(json);
 return {name:options.name??"matrix.json",size:options.size??bytes.byteLength,
  arrayBuffer:options.arrayBuffer??(async()=>bytes.buffer)};
}
function candidate(ids){
 return JSON.stringify({schema:SCHEMA,sources:ids.map(id=>({id,title:"Title "+id,year:null,doi:""})),claims:[]});
}
test("HTML exposes labeled preview, status and confirmation controls",async()=>{
 const html=await readFile(new URL("./index.html",import.meta.url),"utf8");
 for(const id of ["import-preview","import-summary","confirm-import","cancel-import","status"])
  assert.match(html,new RegExp('id="'+id+'"'));
 assert.match(html,/role="status"/);
 assert.match(html,/aria-describedby="import-help"/);
});
test("initial source is preserved when replacement is only previewed",async()=>{
 node("source").fields=[["id","0007"],["title","Original"],["year",""],["doi",""]];
 await emit("source","submit");
 assert.match(node("counts").textContent,/1 sources/);
 node("upload").files=[fileFor(candidate(["0010","0020"]))];
 await emit("upload","change");
 assert.equal(node("import-preview").hidden,false);
 assert.match(node("import-summary").textContent,/Replace the current 1 sources/);
 assert.match(node("counts").textContent,/1 sources/);
 assert.equal(focused,"confirm-import");
 assert.match(node("sources").items[0].textContent,/0007/);
});
test("cancel preserves current data and clears pending replacement",async()=>{
 await emit("cancel-import","click");
 assert.equal(node("import-preview").hidden,true);
 assert.match(node("counts").textContent,/1 sources/);
 assert.equal(focused,"upload");
 assert.match(node("status").textContent,/cancelled/i);
});
test("invalid JSON is rejected without changing current matrix",async()=>{
 node("upload").files=[fileFor('{"schema":')];
 await emit("upload","change");
 assert.equal(node("import-preview").hidden,true);
 assert.match(node("error").textContent,/Invalid JSON/);
 assert.equal(focused,"error");
 assert.match(node("counts").textContent,/1 sources/);
});
test("explicit confirmation replaces matrix while retaining zero-padded IDs",async()=>{
 node("upload").files=[fileFor(candidate(["0010","0020"]))];
 await emit("upload","change");
 await emit("confirm-import","click");
 assert.equal(node("import-preview").hidden,true);
 assert.match(node("counts").textContent,/2 sources/);
 assert.deepEqual(node("sources").items.map(x=>x.textContent.split(" — ")[0]),["0010","0020"]);
 assert.match(node("status").textContent,/confirmed/i);
});
test("older asynchronous read cannot replace a newer selected file",async()=>{
 let resolveOld;
 const oldPromise=new Promise(resolve=>{resolveOld=resolve});
 const oldBytes=new TextEncoder().encode(candidate(["old"]));
 node("upload").files=[fileFor("",{size:oldBytes.byteLength,arrayBuffer:()=>oldPromise})];
 const older=emit("upload","change");
 node("upload").files=[fileFor(candidate(["new"]))];
 await emit("upload","change");
 resolveOld(oldBytes.buffer);
 await older;
 assert.match(node("import-summary").textContent,/with 1 sources/);
 await emit("confirm-import","click");
 assert.equal(node("sources").items[0].textContent.startsWith("new —"),true);
});
test("adding a source invalidates a pending import",async()=>{
 node("upload").files=[fileFor(candidate(["pending"]))];
 await emit("upload","change");
 node("source").fields=[["id","local-2"],["title","Additional"],["year",""],["doi",""]];
 await emit("source","submit");
 assert.equal(node("import-preview").hidden,true);
 await emit("confirm-import","click");
 assert.match(node("error").textContent,/Choose a valid JSON file/);
 assert.equal(node("sources").items.some(x=>x.textContent.startsWith("local-2 —")),true);
});
test("mismatched file bytes are rejected without replacement",async()=>{
 node("upload").files=[fileFor(candidate(["bad"]),{size:123456})];
 await emit("upload","change");
 assert.match(node("error").textContent,/File size changed/);
 assert.equal(node("import-preview").hidden,true);
});

test("imported 1,600 candidate pairs announce the full count while rendering at most 1,000",async()=>{
 const sources=Array.from({length:80},(_,i)=>({id:"S"+i,title:"Synthetic "+i,year:null,doi:""}));
 const claims=sources.map((s,i)=>({
  id:"C"+i,sourceId:s.id,question:"Question",summary:"Synthetic finding",
  stance:i<40?"supports":"challenges",locator:"p",methods:"m",limitations:"l",quote:""
 }));
 node("upload").files=[fileFor(JSON.stringify({schema:SCHEMA,sources,claims}))];
 await emit("upload","change");
 await emit("confirm-import","click");
 assert.match(node("counts").textContent,/1,600|1600/);
 assert.match(node("counts").textContent,/600 additional pairs not displayed/);
 assert.equal(node("tensions").items.length,1000);
 assert.match(node("tensions").items[0].textContent,/C0 \/ C40/);
 assert.equal(node("claims").items.length,80);
});
