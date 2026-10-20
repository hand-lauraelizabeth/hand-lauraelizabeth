/** Browser-local, source-conscious evidence coverage. Human review is required. */
import {evaluateMatrix} from './core.mjs';

export function evaluateWithProvenance(input){
 if(!input || !Array.isArray(input.criteria)) throw Error('Invalid criteria');
 for(const criterion of input.criteria){
  if(criterion && criterion.mandatory !== undefined && typeof criterion.mandatory !== 'boolean')
   throw Error('Mandatory must be a boolean');
 }
 const result=evaluateMatrix(input);
 const sourceMissing=result.criteria.some(c=>!c.sourceRef.trim());
 return {...result,comparisons:result.comparisons.map(v=>({
  ...v,scorePercent:sourceMissing?null:v.scorePercent
 }))};
}

const csvCell=value=>{
 const s=String(value??'');
 const normalized=s.normalize('NFKC');
 const leading=normalized.replace(/^[\p{Cf}\s\uFEFF]+/u,'');
 if(/^[=+@-]/u.test(leading)||/[,;"'\t\r\n][\p{Cf}\s\uFEFF]*[=+@-]/u.test(normalized)||/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/u.test(normalized))
  throw Error('CSV export blocked: potentially executable spreadsheet content. Use JSON for exact, lossless data.');
 return '"'+s.replaceAll('"','""')+'"';
};

/** Re-evaluate source records rather than trusting imported comparison scores. */
export function exportEvidenceCoverageCSV(saved){
 if(saved?.schema!=='rfp-evaluation-v1'||!Array.isArray(saved.criteria)||!Array.isArray(saved.vendors)||!Array.isArray(saved.ratings))
  throw Error('Invalid RFP result');
 const vendors=saved.vendors.map(v=>{
  const cents=v?.priceCents;
  if(cents!==null&&(!Number.isSafeInteger(cents)||cents<0||cents>999999999999))
   throw Error('Invalid saved price cents');
  return {id:v.id,name:v.name,conflict:v.conflict,price:cents===null?'':(cents/100).toFixed(2)};
 });
 const result=evaluateWithProvenance({criteria:saved.criteria,vendors,ratings:saved.ratings});
 const cols=['vendorId','vendorConflictStatus','vendorPriceCents','vendorReviewIssues','criterionId','score','evidenceRef','note','reviewer','criterionSourceRef','mandatory','reviewIssues'];
 const ratings=new Map(result.ratings.map(r=>[JSON.stringify([r.vendorId,r.criterionId]),r]));
 const lines=[cols.join(',')];
 for(const v of result.vendors) for(const c of result.criteria){
  const r=ratings.get(JSON.stringify([v.id,c.id]));
  const vendorIssues=[];const issues=[];
  if(v.conflict!=='none')vendorIssues.push('Conflict review required: '+v.conflict);
  if(v.priceCents===null)vendorIssues.push('Price not supplied; compare separately');
  if(!r)issues.push('Rating record missing');
  if(!r||r.score===null)issues.push('Score missing');
  if(!r?.evidenceRef?.trim())issues.push('Evidence reference missing');
  if(!c.sourceRef.trim())issues.push('Criterion source missing');
  if(c.mandatory&&r?.score!=null&&r.score<3)issues.push('Mandatory criterion requires human review');
  const row=[v.id,v.conflict,v.priceCents??'',vendorIssues.join('; '),c.id,r?.score??'',r?.evidenceRef??'',r?.note??'',r?.reviewer??'',c.sourceRef,String(c.mandatory),issues.join('; ')];
  lines.push(row.map(csvCell).join(','));
 }
 return lines.join('\r\n')+'\r\n';
}
