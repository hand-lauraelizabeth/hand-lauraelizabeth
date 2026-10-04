# Dimension Composition & Explicit Preference Weight Scenario Contract

**Status:** executable dimension composition and explicit-priority scenario generation implemented. Production weights and recommendation release remain gated.

## Purpose

Provide the governed transition from normalized registered features to recommendation dimensions, then from explicit user priorities to scenario weights. This is deliberately split into two operations so within-dimension feature construction cannot be confused with between-dimension user preference weighting.

## Inputs

### Normalized feature evidence

Required:

- `candidate_id`
- `feature_id`
- `dimension`
- `normalized_value`
- `evidence_state`

Only comparison features admitted by the feature registry should reach this input.

### Composition policy

Required:

- `feature_id`
- `within_dimension_weight`
- `partial_policy`

Allowed partial policies:

- `block`: any missing feature blocks the dimension value;
- `renormalize_observed`: compose from observed features and retain `partial_renormalized` status plus explicit coverage.

A dimension must use one consistent partial policy. Partial renormalization is therefore an explicit policy choice, not an automatic convenience.

### Explicit dimension preferences

Required:

- `dimension`
- `importance`
- `priority_explicit`

Only rows with `priority_explicit=true` generate weights.

## Within-dimension composition

For each candidate and dimension, the tool reports:

- `dimension_value`
- `dimension_status`
- `dimension_coverage_rate`
- expected feature weight
- observed feature weight
- partial policy

The contribution file retains each feature's normalized value, weight, evidence state, and policy.

### Coverage is not desirability

`dimension_coverage_rate` describes evidence completeness. It is not added to the dimension value and cannot raise a candidate's fit simply because more data are available.

## Partial evidence

The earlier candidate-normalization specification required partial renormalization to be explicitly allowed. This composer enforces that boundary: missing features do not automatically cause the remaining observed features to absorb their weight.

This should also be reflected in any earlier standalone normalizer implementation so both stages share the same semantics.

## Between-dimension weights

User importance values are normalized only across **explicitly prioritized dimensions**. A dimension the user did not prioritize receives no inferred baseline weight.

This means the system does not silently assume, for example, that affordability, prestige/selectivity, earnings, geography, or transfer convenience matter equally—or at all—when the user has not said so.

## Sensitivity scenarios

For every explicit baseline dimension the tool can generate:

- baseline normalized weights;
- positive relative perturbation;
- negative relative perturbation;
- leave-one-dimension-out scenario.

The perturbation magnitude is a configuration input, not a claim about the correct uncertainty range. Generated scenarios feed the existing recommendation sensitivity harness.

## No forced ranking when profile is incomplete

If there are no explicit priority dimensions, the tool produces no weight scenarios. The product may still show eligible candidates and contextual evidence, but it should not manufacture a ranked recommendation from unstated preferences.

## Outputs

- `composed_candidate_dimensions.csv`
- `dimension_feature_contributions.csv`
- `explicit_preference_weight_scenarios.csv`
- `dimension_composition_weight_scenario_qa.json`

## Auditability

A recommendation experiment can now be traced through:

source evidence → feature registry → normalization → within-dimension composition → explicit user priority → scenario weight → sensitivity result → explanation.

No stage requires reconstructing a hidden formula from a final score.

## Next implementation block

Build the **recommendation pipeline orchestrator and release gate**. It should connect candidate eligibility, feature registration, pre-score evidence audit, normalization, dimension composition, sensitivity, coverage/fairness diagnostics, and explanation QA; collect their QA artifacts; and emit a machine-readable release decision. The release gate must fail closed when required stages are missing, unresolved review triggers remain, or validation artifacts do not meet explicitly configured criteria. It should not invent acceptance thresholds.
