# Recommendation Sensitivity & Stability Contract

**Status:** executable validation harness implemented; empirical thresholds and production weights intentionally unset.

## Purpose

A recommendation should not look precise when small, defensible changes in assumptions radically change its rank. This layer measures that instability before a weighting scheme is accepted.

The harness operates on already-normalized recommendation dimensions. It does not decide how raw source variables should be normalized and does not invent a preferred weighting scheme.

## Required inputs

### Candidate dimension table

One row per candidate with:

- stable `candidate_id` (or explicitly supplied ID column)
- one numeric column per recommendation dimension included in the tested scenarios

Missing dimension values are rejected. Missingness must first pass through the pre-score evidence audit and an explicit treatment decision; this harness will not silently impute.

### Weight scenario table

One row per scenario × dimension:

- `scenario_id`
- `dimension`
- `weight`

Weights must be nonnegative. They are normalized within each scenario, so scenarios may be expressed as proportions or relative weights.

No default weights are embedded in code.

## Scenario families to test

When substantive weighting work begins, approved scenarios should include:

1. proposed baseline
2. plausible user-preference emphasis scenarios
3. modest perturbations around baseline
4. alternative evidence-quality treatments
5. explicitly approved missing-data treatments
6. geographic-market alternatives where the user has selected them
7. normalization alternatives where defensible

The harness automatically prepares leave-one-dimension-out scenario weights when a scenario is explicitly named `baseline`. Those scenarios must be run through the same scoring harness in a subsequent pass; their existence does not itself constitute a result.

## Outputs

### `recommendation_sensitivity.csv`

Candidate score/rank under every supplied scenario, including top-k membership.

### `recommendation_stability.csv`

For each candidate:

- best rank
- worst rank
- mean rank
- rank standard deviation
- rank range
- top-k count
- top-k persistence
- score range

### `recommendation_leave_one_out_scenarios.csv`

Normalized weight definitions for baseline leave-one-dimension-out tests.

### `recommendation_sensitivity_summary.json`

Run-level counts and basic stability summary.

## Interpretation rules

- Rank movement is evidence about model dependence, not an automatic penalty.
- A candidate that remains top-k across many defensible scenarios is more robust than one whose placement depends on a narrow weighting choice.
- A candidate with high instability should receive an uncertainty/stability explanation if eventually displayed.
- Do not invent a universal acceptable rank-range threshold before observing real candidate sets.
- Score differences are not probabilities and should not be displayed as such.
- Tiny numeric score differences should not be translated into strong ordinal language without validation.

## Weighting governance

Production weights should be justified by the tool's decision purpose and, where appropriate, user-stated priorities. They should not be tuned merely to reproduce the historical model, a preferred institutional ordering, prestige rankings, or anecdotal expectations.

The recovered historical model remains design history: its preference capture, normalization, Reach/Target/Safety framing, and tie-breaking can inform hypotheses, but current weights must be revalidated against the current evidence architecture.

## Next validation block

Implement the **coverage/fairness diagnostic** before finalizing scoring. It should test whether missingness, evidence strength, unresolved identities, and eventual recommendation stability differ systematically across institutional contexts such as sector, award level, community-college status, modality, geography, and transfer-serving status. Protected-class analyses should only be added where lawful, appropriate, sufficiently powered, and supported by data governance.
