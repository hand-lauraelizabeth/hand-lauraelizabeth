# Candidate Set & Dimension Normalization Specification

**Status:** modeling boundary defined; executable candidate builder follows this contract. Production weights remain unset.

## 1. Unit of recommendation

The primary recommendation candidate is **institution × program** rather than institution alone.

Canonical identity:

`candidate_id = UNITID + program_identity`

where `program_identity` is an authoritative program identifier when available and otherwise a reviewed program/CIP identity. Program title text alone is not a stable identifier.

Why this level:

- cost, admissions context, location, control, and institution characteristics often live at institution level;
- academic fit and career pathways require program-level evidence;
- transfer applicability may vary by receiving program;
- field-of-study outcomes can differ materially within the same institution.

An institution-only browse view may exist, but it must not imply that every program at that institution shares the same career, transfer, or outcome evidence.

## 2. Transfer-path variants

Transfer pathways are **evidence attached to a candidate**, not separate candidates by default.

Create a pathway variant only when the user's starting context makes two routes to the same institution × program materially different, for example:

- different sending institutions;
- different articulated programs;
- different guaranteed/admission conditions;
- materially different credit applicability or time-to-degree implications.

When a variant is necessary:

`candidate_variant_id = candidate_id + sending_context + pathway_identity`

Do not duplicate candidates merely because multiple equivalent source records describe the same pathway.

## 3. Candidate-universe inclusion

A row may enter the pre-filter candidate universe when:

1. institution identity is resolved to the current institution universe;
2. the institution is in-scope for the selected search universe;
3. program identity is resolved sufficiently for the requested academic search;
4. the program is not known to be inactive for the applicable source vintage;
5. required lineage fields are present.

Missing optional outcome, labor-market, transfer, or admissions evidence does **not** by itself remove a candidate.

The current Scorecard technical documentation explicitly distinguishes operating status and unmatched reporting units; source-universe membership and identity therefore remain evidence states rather than assumptions.

## 4. Hard constraints vs preferences

### Hard constraints

A hard constraint determines eligibility only when the user explicitly requires it or when it is logically necessary to satisfy the query.

Examples:

- required credential/award level;
- required program/field;
- explicit maximum location/radius or state restriction;
- explicit modality requirement;
- explicit maximum price/debt constraint where the user states it as a ceiling;
- required transfer pathway/receiving-program availability;
- accreditation/licensure requirement when necessary for the stated goal.

Hard constraints must produce a reason code and source/evidence state. Unknown evidence cannot silently become `fails_constraint`.

Allowed constraint outcomes:

- `pass`
- `fail`
- `unknown`
- `not_applicable`

Default behavior: `unknown` remains visible for review/choice rather than being converted to failure, unless the user has explicitly chosen a conservative `exclude_unknown` policy for that constraint.

### Preferences

Preferences affect comparison among eligible candidates. Examples include lower cost, proximity, institution size, selectivity context, transfer convenience, local labor-market strength, or career alignment.

Preferences must not masquerade as eligibility rules.

## 5. Dimension model

The normalized comparison layer retains separate dimensions:

- `college_fit`
- `affordability`
- `academic_program_fit`
- `transfer_pathway_fit`
- `admissions_context`
- `career_pathway_fit`
- `current_labor_market_evidence`
- `geographic_fit`
- `transit_access_fit`
- `walkability_fit`
- `housing_context_fit`
- `accessibility_evidence_fit`

Evidence quality/coverage is stored alongside these values; it is **not** a desirability score. Richer data coverage must not make a candidate appear intrinsically better.

## 6. Normalization contract

Each raw feature used in a dimension must have a manifest row declaring:

- source field;
- dimension;
- direction (`higher_better`, `lower_better`, `target`, `categorical_match`);
- transform;
- valid range/domain;
- missingness behavior;
- clipping/winsorization rule if any;
- reference population;
- source vintage;
- rationale.

No normalization rule is inferred from column names.

### Permitted transform families

Initial supported transforms:

- `identity_0_1`: input already has a validated 0–1 meaning;
- `minmax_reference`: scale against a declared reference population, not only the current result set;
- `percentile_reference`: empirical percentile within a declared reference population;
- `target_distance`: closeness to an explicit user target/tolerance;
- `categorical_match`: explicit mapping defined in the manifest.

The first implementation should prioritize `identity_0_1` and explicit reference-bound min-max transforms. Percentile/target/categorical transforms should be added only with test fixtures and documented semantics.

## 7. Result-set independence

A candidate's normalized value should not change merely because an unrelated candidate enters or leaves the current search results.

Therefore, min/max or percentile reference values must come from a versioned reference population (for example, the relevant current institution/program universe), not the ad hoc displayed result set.

## 8. Missingness

Normalization does not impute missing values.

For each feature, output both:

- normalized value, nullable;
- evidence/missingness state.

The dimension aggregator must know how much of the intended dimension evidence is observed. A dimension based on one observed feature out of five must not be presented with the same apparent confidence as a fully observed dimension.

Missingness remains governed by the pre-score audit states (`unknown`, `suppressed`, `not_pre_evaluated`, `unresolved_identity`, `not_published_for_geography`, `source_not_covered`, etc.).

## 9. Directionality

Direction is explicit and semantic.

Examples:

- lower net price may be better **relative to the user's affordability objective**, but price alone is not quality;
- higher earnings are not automatically better if the career pathway does not match the user's goal;
- higher admissions rate is not inherently better or worse;
- higher local employment is context, not a universal desirability rule;
- selectivity/prestige is not a default positive signal.

The manifest must document why a feature has directional scoring at all.

## 10. Dimension aggregation

Within a dimension, feature weights must be explicit and versioned. Aggregate only over observed eligible features, while separately reporting coverage.

A dimension output should contain at minimum:

- `dimension_value`
- `observed_feature_count`
- `expected_feature_count`
- `dimension_coverage_rate`
- `dimension_evidence_state`

Renormalizing feature weights over observed features is permitted only when the manifest explicitly allows it and the explanation layer reports partial evidence. Otherwise leave the dimension unresolved.

## 11. Admissions context

Admissions evidence should remain contextual rather than being converted prematurely into a probability of admission. Reach/Target/Safety concepts from the historical model may be retained as hypotheses for later calibration, but current labels require validated applicant-context logic and must not be inferred solely from institution-level averages.

## 12. Career pathway semantics

CIP↔SOC is many-to-many pathway evidence. A program's career dimension may aggregate multiple occupations only under an explicit pathway rule. Do not pick the highest-wage SOC as if it were the program outcome, and do not interpret an occupational projection as a guaranteed graduate outcome.

## 13. Geographic semantics

Institution-local OEWS evidence and user geographic preference are distinct:

- institution-local market;
- home market;
- intended destination market;
- remote/national market;
- user-selected comparison market.

The candidate model must identify which geography a labor-market signal describes.

## 14. QA gates

Before scoring:

1. candidate IDs unique at declared grain;
2. no institution-only record silently substitutes for a requested program candidate;
3. hard-constraint outcomes have evidence states;
4. unknown constraints are not silently failed;
5. normalized observed values remain within declared output bounds;
6. missing raw values remain missing after normalization;
7. reference population/version recorded;
8. direction and transform defined for every normalized feature;
9. dimension coverage emitted separately from dimension value;
10. no evidence-coverage variable used as desirability unless explicitly justified and validated.

## Next implementation block

Implement the executable candidate-set builder and feature normalizer against this contract, with a versioned feature manifest and QA outputs. Then connect its dimension table to the existing pre-score, sensitivity, coverage/fairness, and explanation validation layers.
