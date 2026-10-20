/** FT-07: transparent, browser-local RFP comparison; NOT an award decision. */
const textField=(v,name,max=200,required=true)=>{if(typeof v!=='string'||v.length>max||v.includes('\0')||(required&&!v.trim()))throw Error(name+': invalid text');return v};
const unique=(arr,name)=>{const s=new Set();for(const x of arr){if(s.has(x))throw Error('Duplicate '+name+': '+x);s.add(x)}};
export function parsePrice(value){if(value===''||value===null||value===undefined)return null;if(typeof value!=='string'||!/^(0|[1-9]\d{0,9})(?:\.\d{1,2})?$/.test(value))throw Error('Price must be nonnegative dollars with up to two decimals');const [a,b='']=value.split('.');return Number(a)*100+Number(b.padEnd(2,'0'))}
export function evaluateMatrix({criteria,vendors,ratings}){
if(!Array.isArray(criteria)||!criteria.length||criteria.length>30)throw Error('Use 1–30 criteria');
if(!Array.isArray(vendors)||!vendors.length||vendors.length>30)throw Error('Use 1–30 vendors');
if(!Array.isArray(ratings)||ratings.length>900)throw Error('Too many ratings');
const cs=criteria.map(c=>{if(!c||typeof c!=='object')throw Error('Invalid criterion');const id=textField(c.id,'Criterion ID',100);const label=textField(c.label,'Criterion label');const weight=(typeof c.weight==='number'||(typeof c.weight==='string'&&/^(0|[1-9]\d{0,2})$/.test(c.weight)))?Number(c.weight):NaN;if(!Number.isInteger(weight)||weight<0||weight>100)throw Error('Weight must be whole 0–100');return {id,label,weight,mandatory:c.mandatory===true,sourceRef:textField(c.sourceRef??'','Criterion source',300,false)}});
unique(cs.map(x=>x.id),'criterion ID');if(cs.reduce((n,c)=>n+c.weight,0)!==100)throw Error('Criterion weights must total 100');
const vs=vendors.map(v=>{if(!v||typeof v!=='object')throw Error('Invalid vendor');const conflict=v.conflict??'unreviewed';if(!['none','declared','unreviewed'].includes(conflict))throw Error('Invalid conflict status');return {id:textField(v.id,'Vendor ID',100),name:textField(v.name,'Vendor name'),conflict,priceCents:parsePrice(v.price??'')}});
unique(vs.map(x=>x.id),'vendor ID');
const cids=new Set(cs.map(c=>c.id)),vids=new Set(vs.map(v=>v.id)),keys=new Set();
const rs=ratings.map(r=>{if(!r||typeof r!=='object')throw Error('Invalid rating');const vendorId=textField(r.vendorId,'Rating vendor ID',100),criterionId=textField(r.criterionId,'Rating criterion ID',100);if(!vids.has(vendorId)||!cids.has(criterionId))throw Error('Unknown rating reference');const key=JSON.stringify([vendorId,criterionId]);if(keys.has(key))throw Error('Duplicate vendor–criterion rating');keys.add(key);const score=(r.score===null||r.score===''||r.score===undefined)?null:((typeof r.score==='number'||(typeof r.score==='string'&&/^[0-5]$/.test(r.score)))?Number(r.score):NaN);if(score!==null&&(!Number.isInteger(score)||score<0||score>5))throw Error('Score must be 0–5 or missing');return {vendorId,criterionId,score,evidenceRef:textField(r.evidenceRef??'','Evidence reference',300,false),note:textField(r.note??'','Review note',1000,false),reviewer:textField(r.reviewer??'','Reviewer',120,false)}});
const byKey=new Map(rs.map(r=>[JSON.stringify([r.vendorId,r.criterionId]),r]));
const comparisons=vs.map(v=>{let weighted=0,complete=true;const flags=[];const detail=cs.map(c=>{const r=byKey.get(JSON.stringify([v.id,c.id]));if(!r||r.score===null){complete=false;flags.push('Missing score: '+c.id)}else{weighted+=r.score*c.weight;if(!r.evidenceRef.trim()){complete=false;flags.push('Missing evidence reference: '+c.id)}if(c.mandatory&&r.score<3)flags.push('Mandatory criterion needs human review: '+c.id)}if(!c.sourceRef.trim())flags.push('Criterion source missing: '+c.id);return {criterionId:c.id,weight:c.weight,score:r?.score??null,evidenceRef:r?.evidenceRef??'',reviewer:r?.reviewer??'',note:r?.note??''}});
if(v.conflict!=='none'){complete=false;flags.push('Conflict of interest: '+v.conflict)}if(v.priceCents===null)flags.push('Price not supplied; evaluate separately');
return {vendorId:v.id,name:v.name,conflict:v.conflict,priceCents:v.priceCents,scorePercent:complete?weighted/5:null,reviewFlags:flags,detail}});
return {schema:'rfp-evaluation-v1',criteria:cs,vendors:vs,ratings:rs,comparisons,disclaimer:'Human-reviewed comparison only. No automated vendor selection, eligibility or award determination.'};
}
// Spreadsheet CSV is a view, not a lossless interchange format. OWASP notes
// that prefix escaping can disappear after a spreadsheet application re-saves.
// Block suspect values rather than claiming universal formula neutralization.
const formulaLike = value => {
 const s=String(value??'').normalize('NFKC');
 const trimmed=s.replace(/^[\p{Cf}\p{M}\s\uFEFF]+/u,'');
 return /^[=+@-]/u.test(trimmed)
   || /[,;"'\t\r\n][\p{Cf}\p{M}\s\uFEFF]*[=+@-]/u.test(s)
   || /[\u0000-\u0008\u000B\u000C\u000E-\u001F]/u.test(s);
};
const cell=v=>{const s=String(v??'');if(formulaLike(s))throw Error('CSV export blocked: potentially executable spreadsheet content. Use JSON for exact, lossless data.');return '"'+s.replaceAll('"','""')+'"'};
export function exportMatrixJSON(result){if(result?.schema!=='rfp-evaluation-v1')throw Error('Invalid RFP result');return JSON.stringify(result,null,2)+'\n';}
export function exportMatrixCSV(result){const cols=['vendorId','name','conflict','priceCents','scorePercent','reviewFlags'];return [cols.join(','),...result.comparisons.map(v=>cols.map(k=>cell(k==='reviewFlags'?v.reviewFlags.join('; '):v[k])).join(','))].join('\r\n')+'\r\n'}
export function exportEvidenceCSV(result){const cols=['vendorId','criterionId','score','evidenceRef','note','reviewer'];return [cols.join(','),...result.ratings.map(r=>cols.map(k=>cell(r[k])).join(','))].join('\r\n')+'\r\n'}
