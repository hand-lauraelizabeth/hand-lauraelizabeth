# Baseline Recommendation Materialization & Review Gate Contract

**Status:** explicit-priority baseline materialization, sensitivity handoff, and review-eligibility gating implemented. Production authorization remains deliberately unavailable.

## Purpose

Convert already-composed recommendation dimensions into a deterministic baseline ordering without weakening missing-evidence rules or confusing a calculated score with an approved recommendation.

## Inputs

The baseline materializer consumes composed candidate dimensions and the scenario-weight table produced from explicit user priorities. Only the scenario named `baseline` can create the baseline ordering.

## No hidden preference weights

If no baseline scenario exists, the system emits no ranking.

Baseline weights are normalized across the user's explicit priority dimensions once, globally. They are not renormalized separately for candidates with missing evidence. A dimension omitted by the user receives no weight even when evidence exists.

## Candidate-level missingness

Every baseline-weighted dimension must have a usable composed value. Usable statuses are `complete` and `partial_renormalized`, with the latter allowed only when the earlier within-dimension policy explicitly permitted partial renormalization.

A candidate with an absent, blocked, or otherwise unresolved weighted dimension remains eligible but is marked `unranked_unresolved_weighted_dimension`. The missing dimension names are emitted for explanation/review. Remaining dimensions do not absorb the missing dimension's weight.

## Baseline score and rank

For rankable candidates, `baseline_score = Σ(normalized explicit dimension value × normalized explicit baseline weight)`.

Dimension values must remain in `[0,1]`. The score is a comparison index, not a probability of enrollment, success, satisfaction, employment, or fit in an absolute sense.

Exact score ties share a rank. Candidate ID may provide deterministic row ordering inside an exact tie but does not break the tie semantically. The materializer labels calculated rows `ranked_pending_validation`.

## Sensitivity handoff

The materializer exports a wide candidate-dimension table containing the same explicit baseline dimensions and values used in the baseline score. This is the input to the existing sensitivity harness.

This prevents baseline scoring and stability analysis from silently using different feature sets. Candidates that cannot support the baseline dimensions are not inserted into sensitivity scoring through imputation.

## Review eligibility

A second adapter consumes calculated baseline ranked rows, the baseline ranking summary, and the output of the existing recommendation release gate.

Ranked rows become `eligible_for_review` only when baseline status is `RANKING_READY_FOR_VALIDATION` and the recommendation release decision is `ELIGIBLE_FOR_REVIEW`.

A blocked, missing, or unknown release decision exposes zero review-eligible ranked rows.

## Production boundary

`ELIGIBLE_FOR_REVIEW` is not production authorization. The review adapter always emits `production_authorized: false`. No executable path in this contract can convert a calculated ranking or review-eligible ranking into production approval.

## Outputs

Baseline materializer: `recommendation_baseline_all_candidates.csv`, `recommendation_baseline_ranked.csv`, `recommendation_baseline_unranked.csv`, `recommendation_sensitivity_candidate_dimensions.csv`, and `recommendation_baseline_summary.json`.

Review adapter: `review_eligible_ranked_candidates.csv` and `ranked_result_review_eligibility.json`.

## Validation requirements

A review candidate ranking must be traceable through explicit request priority → explicit weight scenario → composed dimension evidence → baseline score → sensitivity analysis → configured recommendation release gate → review-eligibility adapter.

A numeric ranking alone is insufficient.
