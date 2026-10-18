// Browser-local literature synthesis. Metadata is user-entered, not independently verified.
export const SCHEMA="literature-matrix-v1";
const STANCES=new Set(["supports","challenges","mixed","uncertain"]);
function obj(v,n){if(!v||typeof v!=="object"||Array.isArray(v))throw Error(n+" must be an object");return v}
function str(v,n,max,req=false){if(v==null)v="";if(typeof v!=="string"||v.length>max||/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u.test(v))throw Error(n+" invalid");if(req&&!v.trim())throw Error(n+" required");return v}
function id(v,n){const s=str(v,n,128,true);if(s!==s.trim()||/[\r\n\t]/u.test(s))throw Error(n+" invalid whitespace");return s}
function year(v){if(v==null||v==="")return null;if(!Number.isInteger(v)||v<1400||v>2200)throw Error("Invalid year");return v}
function doi(v){const s=str(v,"DOI",250);if(s&&!/^10\.[0-9]{4,9}\/\S+$/u.test(s))throw Error("Enter a bare, unverified DOI");return s}
export function validateProject(input){
 const p=obj(input,"Project");if(p.schema!==SCHEMA)throw Error("Unsupported schema");
 if(!Array.isArray(p.sources)||!Array.isArray(p.claims)||p.sources.length>500||p.claims.length>2000)throw Error("Record limit");
 const ss=new Set(),cs=new Set();
 const sources=p.sources.map((v,i)=>{const x=obj(v,"Source "+i);const r={id:id(x.id,"Source ID"),title:str(x.title,"Title",500,true),year:year(x.year),doi:doi(x.doi)};if(ss.has(r.id))throw Error("Duplicate source ID");ss.add(r.id);return r});
 const claims=p.claims.map((v,i)=>{const x=obj(v,"Claim "+i);const r={id:id(x.id,"Claim ID"),sourceId:id(x.sourceId,"Source reference"),question:str(x.question,"Question",400,true),summary:str(x.summary,"Finding",1500,true),stance:str(x.stance,"Stance",30,true),locator:str(x.locator,"Locator",180),methods:str(x.methods,"Methods",1000),limitations:str(x.limitations,"Limitations",1000),quote:str(x.quote,"Short excerpt",240)};
 if(!STANCES.has(r.stance)||cs.has(r.id)||!ss.has(r.sourceId))throw Error("Invalid stance, duplicate claim or unknown source");cs.add(r.id);return r});
 return {schema:SCHEMA,sources,claims};
}
export function analyzeProject(input){
 const project=validateProject(input),issues=[],groups=new Map();
 for(const s of project.sources)if(!s.doi)issues.push({kind:"missing-doi",sourceId:s.id});
 for(const c of project.claims){if(!c.locator)issues.push({kind:"missing-locator",claimId:c.id,sourceId:c.sourceId});if(!c.methods)issues.push({kind:"methods-not-recorded",claimId:c.id});if(!c.limitations)issues.push({kind:"limitations-not-recorded",claimId:c.id});if(!groups.has(c.question))groups.set(c.question,[]);groups.get(c.question).push(c)}
 const tensions=[];
 for(const [question,rows] of groups){const yes=rows.filter(x=>x.stance==="supports"),no=rows.filter(x=>x.stance==="challenges");for(const a of yes)for(const b of no)if(a.sourceId!==b.sourceId)tensions.push({question,supportClaimId:a.id,challengeClaimId:b.id,sourceIds:[a.sourceId,b.sourceId],status:"review-user-coded-stances"})}
 return {project,issues,tensions};
}
function bytes(s){return unescape(encodeURIComponent(s)).length}
export function exportProject(input){const json=JSON.stringify(validateProject(input),null,2);if(bytes(json)>2000000)throw Error("Export exceeds 2 MB");return json}
export function importProject(json){if(typeof json!=="string"||bytes(json)>2000000)throw Error("Import exceeds 2 MB");let p;try{p=JSON.parse(json)}catch{throw Error("Invalid JSON")};return validateProject(p)}
