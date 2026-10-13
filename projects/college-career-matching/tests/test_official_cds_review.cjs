"use strict";
const assert=require("node:assert/strict");
const review=require("../ui/official_cds_score_review.js");
const id="institution_cds_una_2025";
const url="https://www.una.edu/research/Institutional%20Data/una-common-data-set-2025-2026.pdf";
const payload={
 source_registry:{[id]:{url,cohort:"Fall 2025",sat_composite_estimated:false,act_reference_field:"CDS_ACT_COMPOSITE_50"}},
 institutions:{"101879":[null,23,1018,1110,1250,20,23,27,id,id]}
};
assert.equal(review.verifySource(payload),true);
assert.equal(review.satLabel(payload.source_registry[id]),"SAT composite (reported percentiles)");
assert.equal(review.actReferenceLabel(payload.source_registry[id]),"reported median");
assert.match(review.policyLabel({policy:"not_considered_for_admission"}),/Not considered/);
assert.throws(()=>review.verifySource({...payload,source_registry:{}}),/attribution invalid/);
assert.throws(()=>review.verifySource({...payload,institutions:{"101879":[1110,23,1018,1110,1250,20,23,27,id,id]}}),/source data invalid/);
assert.equal(review.policyLabel(null),null);
console.log("7 official CDS adapter tests passed");
