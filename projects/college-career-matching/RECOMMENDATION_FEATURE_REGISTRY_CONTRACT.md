# Recommendation Feature Registry Contract

**Status:** declarative feature-to-dimension registry validator implemented. Production feature selections, normalization references, and weights remain subject to validation.

## Purpose

Create one governed bridge between assembled evidence and the recommendation model. A column's presence in a dataset must never be enough to make it part of a recommendation score.

Every field used downstream is registered with a stable feature ID, recommendation dimension, semantic role, direction, source lineage, grain, and normalization policy.

## Recommendation dimensions

The initial registry recognizes:

1. `college_fit`
2. `affordability`
3. `academic_program_fit`
4. `transfer_pathway_fit`
5. `admissions_context`
6. `career_pathway_fit`
7. `current_labor_market_evidence`
8. `long_term_outlook`
9. `geographic_fit`
10. `evidence_quality_coverage`

Current labor-market evidence and long-term outlook are deliberately separate. Evidence quality/coverage is also separate from fit.

## Required registry fields

- `feature_id`: stable semantic identifier
- `source_column`: exact assembled candidate-table column
- `dimension`
- `role`
- `direction`
- `source_family`
- `source_vintage`
- `grain`
- `normalization_policy`

Optional fields can document description, source URL field, evidence-state field, specificity, and notes.

## Roles

### `comparison`
A candidate-comparison feature that may enter normalization and later scenario scoring. It must have an explicit direction and normalization policy.

### `context`
Evidence shown/interpreted alongside a recommendation but not automatically scored.

### `coverage`
Evidence about whether another measure is available/reliable. Coverage must use `direction=none`; richer data coverage cannot itself make a candidate a better fit.

### `explanation_only`
Traceability or descriptive fields retained for explanations but excluded from comparison calculations.

## Direction

Allowed initial values:

- `higher_better`
- `lower_better`
- `target_match`
- `none`

Direction describes the declared semantics of a comparison feature. It does not itself choose a weight.

## No ad hoc feature selection

Downstream normalization and scoring experiments should consume `recommendation_registered_features_long.csv` and registry lineage rather than scanning the candidate table for numeric columns.

This blocks several failure modes:

- accidentally scoring IDs or coverage percentages;
- allowing a newly joined source column to affect recommendations without review;
- silently blending current wages with long-term projections;
- using institutional data at program grain without declaring the grain;
- changing feature meaning when source vintages change.

## Source lineage

Every registered feature declares its source family and vintage. Where a value is derived from several upstream sources, the registry should name the derived feature family while the upstream join/QA artifacts retain component lineage.

A production build should be reproducible from the registry version plus source manifests/snapshots.

## Normalization policy

The registry names the policy but does not define arbitrary reference values in code. Comparison features must point to a separately versioned normalization policy/reference population compatible with the existing candidate-dimension normalizer.

A feature cannot become comparison-ready merely because it is numeric.

## Missing registry columns

If a registry feature's source column is absent from the assembled table, it is written to `recommendation_feature_registry_missing_columns.csv`. This supports staged source availability without silently replacing the feature with another field.

Whether an absent feature blocks a release is handled by the validation/release gate according to its declared requirement level.

## Outputs

- `recommendation_feature_lineage.csv`
- `recommendation_feature_registry_missing_columns.csv`
- `recommendation_registered_features_long.csv`
- `recommendation_dimension_registry_summary.csv`
- `recommendation_feature_registry_qa.json`

## Relationship to user preferences

The registry says what the system *can* compare and how a feature is interpreted. The explicit preference profile says what the user *cares about*. A registered feature should not receive material weight merely because it exists; preference/scenario policy remains a separate governed layer.

## Next implementation block

Build the **dimension composer and preference-to-weight scenario generator**. It should combine normalized registered comparison features into dimension-level values using declared within-dimension policies, then translate only explicit user priorities into baseline and sensitivity weight scenarios. It must keep coverage separate, expose every within-dimension contribution, and avoid inventing weights for dimensions the user did not prioritize.
