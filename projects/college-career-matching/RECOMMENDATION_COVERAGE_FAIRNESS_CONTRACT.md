# Recommendation Coverage & Fairness Diagnostic Contract

**Status:** executable institutional-context diagnostic implemented; empirical review thresholds intentionally unset.

## Purpose

Before finalizing a matching model, test whether the data architecture itself gives systematically different evidence quality or recommendation stability to different kinds of institutions/programs. This is primarily a **coverage and measurement audit**. It should identify places where source design, crosswalks, geography, or model assumptions could disadvantage an option before those gaps are mistaken for weak fit.

NCES/IPEDS explicitly supports institutional groupings such as control, level, and sector. Community colleges are not a single directly collected IPEDS flag; NCES notes that public institutions in the relevant associate/certificate categories can be used to isolate that universe. Therefore any `community_college_status` used here must be derived transparently and versioned rather than guessed from institution names.

## Inputs

1. Institutional/program context table: one row per candidate, containing the stable candidate ID and declared grouping fields.
2. `recommendation_input_missingness.csv` from the pre-score evidence audit.
3. `recommendation_review_queue.csv` from the pre-score audit.
4. Optional `recommendation_stability.csv` from the sensitivity harness.

## Initial grouping fields

Use only fields that are defined and versioned in the model-ready universe. Appropriate initial institutional-context diagnostics include:

- IPEDS control
- IPEDS level
- IPEDS sector
- derived community-college status with documented rule
- award level / credential level
- degree-granting status
- modality / distance-education context where available
- state / region
- metropolitan vs nonmetropolitan local-market context
- transfer-serving / articulation-coverage status
- source-coverage family

These fields are diagnostic slices, not automatic score modifiers.

## What the executable measures

For every declared group it reports:

- candidate count
- mean evidence-coverage rate
- share of candidates with review triggers
- mean review-trigger count
- coverage delta versus the overall candidate universe
- review-trigger-rate delta versus overall
- when stability output is supplied: mean rank range, top-k persistence, and rank standard deviation

## Small samples

`--min-n` controls a **small-group interpretation flag**, not a statistical-significance cutoff. The default of 20 is operational only and should be revisited after observing the real universe. Small groups remain in the output; they are not dropped or merged silently.

## Interpretation

A group-level difference can arise from many mechanisms:

- actual source coverage differences
- unresolved identities/crosswalks
- source definitions
- institutional reporting structures
- program mix
- geographic suppression
- transfer-data system coverage
- model normalization
- genuine differences in observed characteristics

Therefore the diagnostic must not label a group biased/unbiased merely because a numeric delta exceeds an arbitrary threshold. Large or persistent differences enter a review queue for investigation.

## Community-college safeguard

Community colleges are especially important because a four-year-centered data architecture can accidentally create apparent evidence deficits. The audit should separately examine whether community-college candidates have:

- lower program/CIP coverage
- lower transfer/articulation evidence coverage
- different Scorecard outcome availability
- more unresolved identities
- lower local labor-market coverage
- greater recommendation instability

A coverage deficit must not become a negative recommendation signal.

## Modality safeguard

Distance education is a distinct institutional/student context in IPEDS. Local labor-market evidence should not be assumed to represent the relevant post-completion market for a fully online program or geographically dispersed student body. Modality should therefore be available as a diagnostic/context field and later interact with user-selected geography rather than silently altering local-market evidence.

## Protected attributes

This institutional-context audit does not require protected-class attributes and does not use them to alter recommendations. Any future protected-class validation should be added only where lawful, appropriate, sufficiently powered, privacy-preserving, and supported by explicit data governance. Coverage/error disparities and recommendation-outcome disparities should remain separate analyses.

## Outputs

- `recommendation_candidate_diagnostic.csv`
- `recommendation_group_coverage_diagnostic.csv`
- `recommendation_group_review_queue.csv`
- `recommendation_coverage_fairness_summary.json`

## Release gate

Before production scoring, reviewers should be able to answer:

1. Which institutional contexts have weaker evidence coverage?
2. Is the difference caused by the source universe, identity resolution, or model design?
3. Does missing evidence reduce a candidate's score, directly or indirectly?
4. Are recommendations materially less stable for any context?
5. Can the issue be corrected upstream, or must uncertainty be displayed?
6. Are community-college, transfer, online, and nonmetropolitan options represented on substantively appropriate evidence rather than four-year/residential/metro assumptions?

## Next implementation block

Implement the **recommendation explanation contract** as structured output: reason codes, tradeoffs, missing/uncertain evidence, source specificity, conditions, stability, and human-review status. Explanations should be generated from auditable evidence fields rather than free-form post-hoc rationalization.
