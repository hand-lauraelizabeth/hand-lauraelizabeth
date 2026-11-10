/** Local, descriptive drill-down of unresolved vendor–criterion evidence.
 * Preserves exact source identifiers. Does not recommend or award vendors.
 */
import {summarizeCoverage} from './coverage-summary.mjs';
import {hasVisibleReference} from './evidence-coverage.mjs';

export function listEvidenceGaps(result){
 summarizeCoverage(result); // Validate the evaluated comparison shape and IDs.
 if(result.criteria.length>30||result.vendors.length>30)
  throw Error('Too many vendor–criterion pairs');
 const gaps=[];
 for(const comparison of result.comparisons){
  for(let index=0;index<result.criteria.length;index++){
   const criterion=result.criteria[index],detail=comparison.detail[index];
   const issues=[];
   if(detail.score===null)issues.push('Score missing');
   if(!hasVisibleReference(criterion.sourceRef))issues.push('Criterion source missing');
   if(detail.score!==null&&!hasVisibleReference(detail.evidenceRef))issues.push('Evidence reference missing');
   if(detail.score!==null&&!hasVisibleReference(detail.reviewer))issues.push('Reviewer identifier missing');
   if(issues.length)gaps.push(Object.freeze({
    vendorId:comparison.vendorId,criterionId:criterion.id,score:detail.score,
    criterionSourceRef:criterion.sourceRef,evidenceRef:detail.evidenceRef,
    reviewer:detail.reviewer,issues:Object.freeze(issues)
   }));
  }
 }
 return Object.freeze(gaps);
}
