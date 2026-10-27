/** Human-review coverage counts for browser-local RFP comparisons.
 * Counts are descriptive, not a ranking or an award recommendation.
 */
import {hasVisibleReference} from './evidence-coverage.mjs';

export function summarizeCoverage(result){
  if(result?.schema!=='rfp-evaluation-v1'||!Array.isArray(result.criteria)||
     !Array.isArray(result.comparisons)||!Array.isArray(result.vendors)||
     result.comparisons.length!==result.vendors.length)
    throw Error('Invalid evaluated RFP coverage');
  const totalPairs=result.criteria.length*result.vendors.length;
  let scoredPairs=0, documentedPairs=0, attributedPairs=0;
  for(const comparison of result.comparisons){
    if(!Array.isArray(comparison.detail)||comparison.detail.length!==result.criteria.length)
      throw Error('Invalid evaluated RFP details');
    for(let i=0;i<result.criteria.length;i++){
      const detail=comparison.detail[i],criterion=result.criteria[i];
      if(!detail||detail.criterionId!==criterion.id)
        throw Error('Invalid evaluated RFP criterion reference');
      if(detail.score!==null){
        scoredPairs++;
        if(hasVisibleReference(detail.reviewer))attributedPairs++;
        if(hasVisibleReference(detail.evidenceRef)&&hasVisibleReference(criterion.sourceRef))
          documentedPairs++;
      }
    }
  }
  const withheld=result.comparisons.filter(v=>v.scorePercent===null).length;
  const conflictReview=result.vendors.filter(v=>v.conflict!=='none').length;
  const missingPrices=result.vendors.filter(v=>v.priceCents===null).length;
  return Object.freeze({
    totalPairs,scoredPairs,documentedPairs,missingScores:totalPairs-scoredPairs,
    scoredWithoutReferences:scoredPairs-documentedPairs,
    scoredWithoutReviewer:scoredPairs-attributedPairs,
    withheld,conflictReview,missingPrices
  });
}

export function describeCoverage(result){
  const c=summarizeCoverage(result);
  return `Coverage: ${c.scoredPairs} of ${c.totalPairs} vendor–criterion pairs scored; ${c.documentedPairs} scored pairs have visible evidence and criterion source; ${c.missingScores} missing scores; ${c.scoredWithoutReferences} scored pairs missing evidence or source; ${c.scoredWithoutReviewer} scored pairs missing a visible reviewer identifier; ${c.withheld} proposal scores withheld; ${c.conflictReview} conflict statuses require review; ${c.missingPrices} prices not supplied. Counts are descriptive, not an award decision.`;
}
