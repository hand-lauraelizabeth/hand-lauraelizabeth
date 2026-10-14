'use strict';
// Review-only overlay decorator. Never mutate the immutable Scorecard tuples.
const POLICY_GATES=Object.freeze({'208822':{status:'not_considered',source:'George Fox University 2025-26 Common Data Set'}});
function decoratePinnedScores(overlay, id, evidence={}) {
  id=String(id);
  if(!/^\d{6}$/.test(id)) return null;
  if(!overlay || overlay.school_count!==6243 || !overlay.institutions) throw Error('Unexpected pinned overlay');
  const baseline=Object.prototype.hasOwnProperty.call(overlay.institutions,id)?overlay.institutions[id]:null;
  const extra=Object.prototype.hasOwnProperty.call(evidence,id)?evidence[id]:null;
  if(baseline && extra) throw Error('Overlay and supplemental score record collide');
  if(!baseline && !extra) return null;
  const policy=POLICY_GATES[id]||null;
  const admissionsCategoryStatus=policy?'prohibited_by_policy':extra?'unverified_do_not_classify':'unchanged_existing_behavior';
  return Object.freeze({unitid:id,baselineTuple:baseline,descriptiveEvidence:extra,policy,admissionsCategoryStatus,admissionsCategoryAllowed:policy?false:extra?false:null});
}
module.exports={decoratePinnedScores,POLICY_GATES};
