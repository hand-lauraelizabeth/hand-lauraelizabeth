import test from "node:test";
import assert from "node:assert/strict";
import {SCHEMA,analyzeProject,exportProject,importProject} from "./core.mjs";

const source=(id)=>({id,title:"Synthetic source "+id,year:null,doi:""});
const claim=(id,sourceId,stance,question="Question")=>({
 id,sourceId,question,summary:"Synthetic finding",stance,locator:"p. 1",
 methods:"Recorded",limitations:"Synthetic only",quote:""
});
const project=(sources,claims)=>({schema:SCHEMA,sources,claims});

test("40 by 40 candidates are capped at 1,000 without hiding the true count",()=>{
 const sources=Array.from({length:80},(_,i)=>source("S"+String(i).padStart(3,"0")));
 const claims=sources.map((s,i)=>claim("C"+i,s.id,i<40?"supports":"challenges"));
 const result=analyzeProject(project(sources,claims));
 assert.equal(result.tensionTotal,1600);
 assert.equal(result.tensions.length,1000);
 assert.equal(result.tensionsOmitted,600);
 assert.deepEqual(result.tensions[0].sourceIds,["S000","S040"]);
 assert.equal(result.tensions[999].supportClaimId,"C24");
 assert.equal(result.tensions[999].challengeClaimId,"C79");
 assert.ok(result.tensions.every(t=>t.status==="review-user-coded-stances"));
});

test("same-source pairings are excluded from total and list",()=>{
 const sources=[source("0001"),source("0002")];
 const claims=[claim("a","0001","supports"),claim("b","0001","challenges"),claim("c","0002","challenges")];
 const result=analyzeProject(project(sources,claims));
 assert.equal(result.tensionTotal,1);
 assert.equal(result.tensionsOmitted,0);
 assert.deepEqual(result.tensions.map(t=>[t.supportClaimId,t.challengeClaimId]),[["a","c"]]);
});

test("different research questions never form candidate pairs",()=>{
 const sources=[source("s1"),source("s2"),source("s3")];
 const claims=[claim("a","s1","supports","Q1"),claim("b","s2","challenges","Q2"),claim("c","s3","challenges","Q1")];
 const result=analyzeProject(project(sources,claims));
 assert.equal(result.tensionTotal,1);
 assert.equal(result.tensions[0].question,"Q1");
 assert.equal(result.tensions[0].challengeClaimId,"c");
});

test("maximal 2,000-claim input counts 1,000,000 pairs without materializing them",()=>{
 const sources=Array.from({length:500},(_,i)=>source("S"+i));
 const claims=[];
 for(let i=0;i<1000;i++)claims.push(claim("A"+i,sources[i%250].id,"supports"));
 for(let i=0;i<1000;i++)claims.push(claim("B"+i,sources[250+i%250].id,"challenges"));
 const p=project(sources,claims);
 const result=analyzeProject(p);
 assert.equal(result.tensionTotal,1000000);
 assert.equal(result.tensions.length,1000);
 assert.equal(result.tensionsOmitted,999000);
 assert.equal(result.project.claims.length,2000);
 assert.equal(importProject(exportProject(p)).claims.length,2000);
});

test("capping a rendered list never drops exact IDs from JSON evidence",()=>{
 const sources=Array.from({length:80},(_,i)=>source(String(i).padStart(4,"0")));
 const claims=sources.map((s,i)=>claim("finding-"+String(i).padStart(4,"0"),s.id,i<40?"supports":"challenges"));
 const p=project(sources,claims);
 assert.equal(analyzeProject(p).tensionsOmitted,600);
 const roundtrip=importProject(exportProject(p));
 assert.deepEqual(roundtrip,p);
 assert.equal(roundtrip.claims[79].sourceId,"0079");
});
