/* Official institutional CDS evidence is a review-only supplement to federal scores. */
(function(global){
  "use strict";
  const CDS_ID="institution_cds_una_2025";
  const CDS_URL="https://www.una.edu/research/Institutional%20Data/una-common-data-set-2025-2026.pdf";
  function verifySource(overlay){
    if(!overlay||!overlay.source_registry||!overlay.institutions)throw Error("Missing source registry.");
    const source=overlay.source_registry[CDS_ID];
    if(!source||source.url!==CDS_URL||source.cohort!=="Fall 2025"||
       source.sat_composite_estimated!==false||
       source.act_reference_field!=="CDS_ACT_COMPOSITE_50")
      throw Error("Institutional source attribution invalid.");
    const row=overlay.institutions["101879"];
    if(!Array.isArray(row)||row.length!==10||row[0]!==null||
       JSON.stringify(row.slice(1,8))!==JSON.stringify([23,1018,1110,1250,20,23,27])||
       row[8]!==CDS_ID||row[9]!==CDS_ID)throw Error("CDS source data invalid.");
    return true;
  }
  function satLabel(source){
    return source&&source.sat_composite_estimated===false
      ?"SAT composite (reported percentiles)"
      :"SAT (estimated total percentiles)";
  }
  function actReferenceLabel(source){
    return source&&["ACTCM50","CDS_ACT_COMPOSITE_50"].includes(source.act_reference_field)
      ?"reported median":"reported midpoint";
  }
  function policyLabel(policy){
    if(!policy)return null;
    if(policy.policy==="not_considered_for_admission")
      return "Not considered for admission; may be used for scholarships or placement.";
    return null;
  }
  const api={verifySource,satLabel,actReferenceLabel,policyLabel};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  else global.OfficialCdsScoreReview=api;
})(typeof window!=="undefined"?window:globalThis);
