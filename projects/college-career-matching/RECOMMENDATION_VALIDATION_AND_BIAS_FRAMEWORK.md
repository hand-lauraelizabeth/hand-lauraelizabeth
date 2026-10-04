# Recommendation Validation & Bias Framework

**Status:** pre-scoring governance contract implemented. No production recommendation score should be released until these gates are executable and reviewed.

## Purpose

The College + Career Matching Tool combines heterogeneous evidence: institutional characteristics, cost, admissions context, programs, transfer/articulation, career pathways, national projections, local labor markets, and eventually user preferences. This framework prevents those layers from becoming an opaque rank whose apparent precision exceeds the evidence.

The tool should answer **why a result fits**, **which evidence is missing**, and **how stable the result is** before it claims that one option is better than another.

## 1. Separate recommendation dimensions

Keep at least these dimensions independently inspectable:

1. college/institution fit
2. affordability
3. academic/program fit
4. transfer/pathway fit
5. admissions context
6. career-pathway fit
7. current labor-market evidence
8. geographic fit
9. evidence quality/coverage

A composite display, if later validated, must never erase the component values or their evidence states.

## 2. Missingness policy

Missing data is not neutral by default and is never automatically zero.

Every model input must have a declared missingness behavior:

- `unknown`: evidence absent or unavailable
- `not_applicable`: field genuinely does not apply
- `suppressed`: source withholds estimate
- `not_pre_evaluated`: source has not established a transfer/equivalency rule
- `unresolved_identity`: source record exists but crosswalk is unresolved
- `not_published_for_geography`: no local estimate is published
- `source_not_covered`: source universe does not cover the entity/program

Rules:

- Do not penalize an institution/program merely because a source omits it unless omission itself has validated substantive meaning.
- Do not mean-impute recommendation inputs silently.
- Do not turn suppression into zero.
- Show material missingness in explanations.
- Measure missingness by institution type, sector, award level, geography, and other relevant groups before scoring.

## 3. Evidence confidence

Each recommendation dimension should carry an evidence state separate from the substantive signal. Minimum fields:

- source family/families
- source vintage
- coverage status
- identity-match status
- direct vs inferred evidence
- specificity level
- material conditions/qualifiers
- unresolved-review flag

Suggested display states are `strong evidence`, `partial evidence`, `limited evidence`, and `insufficient evidence`; thresholds must be calibrated from observed coverage rather than invented in advance.

## 4. Sensitivity and stability tests

Before a weighting scheme is accepted, test:

- leave-one-dimension-out ranking movement
- plausible weight perturbations
- missing-data strategy changes
- alternative normalization methods
- source-vintage changes
- local vs state/national labor-market substitutions when explicitly requested
- many-to-many CIP↔SOC pathway alternatives
- transfer evidence at different specificity levels

For each recommendation, calculate a stability summary such as rank range or top-k persistence across approved scenarios. Large instability must be surfaced rather than hidden behind a single score.

## 5. Fairness / subgroup review

The tool should not optimize outcomes by protected class. Where lawful, appropriate, sufficiently powered, and supported by data governance, validation should examine whether recommendation quality or evidence coverage differs materially across relevant user groups or institutional contexts.

At minimum, inspect proxy pathways that can produce inequitable results even without protected-class inputs:

- price/cost assumptions
- geography and commuting assumptions
- full-time vs part-time assumptions
- transfer-student treatment
- community-college coverage
- online/hybrid modality
- program availability
- admissions-selectivity signals
- historical earnings data
- local labor-market concentration

Evaluate coverage/error disparities separately from outcome/ranking disparities. Do not interpret small samples as reliable subgroup findings.

## 6. Accessibility and usability validation

Recommendation quality includes whether the explanation can be used.

Required checks:

- do not encode meaning by color alone
- sufficient contrast
- keyboard-operable controls
- semantic headings/labels
- screen-reader-readable tables and status text
- plain-language explanation alongside technical detail
- no forced precision in percentages/scores
- mobile-readable comparison views
- missing/uncertain evidence expressed textually

## 7. Explanation contract

Every displayed recommendation should be able to provide:

- strongest reasons it fits the user's stated preferences
- important tradeoffs
- material missing/uncertain evidence
- source/vintage for important claims
- whether evidence is institution-, program-, course-, occupation-, or geography-specific
- conditions attached to transfer/pathway claims
- what changed if the user changes a preference or weight

Never state a transfer guarantee, admissions likelihood, affordability conclusion, or career outcome more strongly than the source evidence supports.

## 8. Human-review triggers

Route a recommendation/evidence path for review when any of the following is material:

- unresolved institution/program/course identity
- conflicting authoritative sources
- compound transfer rule not structurally represented
- ambiguous program→CIP mapping
- major data vintage mismatch
- unusually high missingness
- large rank instability under reasonable perturbation
- a recommendation depends heavily on one weak/inferred signal
- outlier values that materially change rank
- source schema drift
- regression coverage loss

Human review should correct evidence or mark uncertainty; it should not silently override data without lineage.

## 9. Pre-release gates

A recommendation model is not production-ready until:

1. source and identity QA passes;
2. missingness audit is complete;
3. weighting rationale is documented;
4. sensitivity tests are run;
5. subgroup/coverage review is run where feasible and appropriate;
6. explanation output passes semantic QA;
7. accessibility review passes;
8. known limitations are visible;
9. regression baselines are versioned;
10. sample recommendations are manually reviewed end-to-end.

## 10. Historical model use

The recovered historical college-matching formulas are design history and evidence of prior modeling work, not an instruction to reproduce an opaque weighted rank. Useful concepts—preference capture, normalization, Reach/Target/Safety context, tie-breaking, and multi-factor comparison—should be independently revalidated against the current data architecture.

## 11. Validation outputs

The executable validation layer should eventually emit:

- `recommendation_input_missingness.csv`
- `recommendation_evidence_coverage.csv`
- `recommendation_sensitivity.csv`
- `recommendation_stability.csv`
- `recommendation_review_queue.csv`
- `recommendation_validation_summary.json`

These artifacts should be versioned with the scoring specification, source manifest, and data vintages.

## Next implementation block

Implement the executable **pre-score evidence audit** first. It should accept a model-ready candidate table plus a field-policy manifest, classify missingness/coverage, identify weak or unresolved evidence, and generate the review queue. Weighting/scoring should remain gated until that audit is operational.
