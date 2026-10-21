/** Browser-local, source-conscious evidence coverage. Human review is required. */
import {evaluateMatrix} from './core.mjs';

// Source/evidence references must contain a visible letter, number, punctuation,
// or symbol. Format controls, separators and isolated combining marks do not
// constitute evidence. Original identifiers and reference text are unchanged.
export const hasVisibleReference = value =>
 typeof value === 'string' && /[\p{L}\p{N}\p{P}\p{S}]/u.test(value);

export function evaluateWithProvenance(input){
 if(!input || !Array.isArray(input.criteria)) throw Error('Invalid criteria');
 for(const criterion of input.criteria){
  if(criterion && criterion.mandatory !== undefined && typeof criterion.mandatory !== 'boolean')
   throw Error('Mandatory must be a boolean');
 }
 const result=evaluateMatrix(input);
 const missingSources=result.criteria.filter(c=>!hasVisibleReference(c.sourceRef));
 return {...result,comparisons:result.comparisons.map(v=>{
  const invisibleEvidence=v.detail.filter(d=>d.score!==null&&!hasVisibleReference(d.evidenceRef));
  const flags=[...v.reviewFlags];
  for(const c of missingSources)if(c.sourceRef.trim())flags.push('Criterion source visually empty: '+c.id);
  for(const d of invisibleEvidence)if(d.evidenceRef.trim())flags.push('Evidence reference visually empty: '+d.criterionId);
  return {...v,scorePercent:missingSources.length||invisibleEvidence.length?null:v.scorePercent,reviewFlags:flags};
 })};
}

const csvCell=value=>{
 const s=String(value??'');
 const normalized=s.normalize('NFKC');
 if(/[\u202A-\u202E\u2066-\u2069]/u.test(s))throw Error('CSV export blocked: explicit bidirectional formatting controls. Use JSON for lossless data.');
 const leading=normalized.replace(/^[\p{Cf}\p{M}\s\uFEFF]+/u,'');
 if(/^[=+@-]/u.test(leading)||/[,;"'\t\r\n][\p{Cf}\p{M}\s\uFEFF]*[=+@-]/u.test(normalized)||/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/u.test(normalized))
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
  if(!hasVisibleReference(r?.evidenceRef))issues.push('Evidence reference missing');
  if(!hasVisibleReference(c.sourceRef))issues.push('Criterion source missing');
  if(c.mandatory&&r?.score!=null&&r.score<3)issues.push('Mandatory criterion requires human review');
  const row=[v.id,v.conflict,v.priceCents??'',vendorIssues.join('; '),c.id,r?.score??'',r?.evidenceRef??'',r?.note??'',r?.reviewer??'',c.sourceRef,String(c.mandatory),issues.join('; ')];
  lines.push(row.map(csvCell).join(','));
 }
 return lines.join('\r\n')+'\r\n';
}
