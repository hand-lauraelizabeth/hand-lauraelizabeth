# Career Preference Alignment Contract

**Status:** pathway-level explicit-preference alignment implemented with operator-specific semantics; scoring calibration remains gated.

## Purpose

Make the career side of the College + Career Matching Tool substantive. Programs should not be recommended merely because linked occupations have high wages or projected growth. The tool compares occupational pathways with what a user explicitly says they value in work.

## Grain

Alignment is calculated first at **occupation pathway** grain, not directly at institution or program grain. One program can connect to multiple occupations with different work characteristics.

## Inputs

Program/candidate pathways must contain `occ_code` and may carry `candidate_id`, `UNITID`, `program_id`, and `cip_code`.

Occupation attributes are long-form `occ_code`, `attribute_id`, `attribute_value`. Appropriate O*NET domains may include interests, work values, skills, knowledge, work activities, work styles, or work context, with source definitions/scales retained upstream.

Explicit career preferences contain:

- `preference_id`
- `attribute_id`
- `operator`
- `target_value`
- `importance`
- `priority_explicit`
- `scale_min`, `scale_max` for numeric operators
- `target_min`, `target_max` for range preferences

Only `priority_explicit=true` rows participate.

## Operator semantics

A preference must declare what “better aligned” means. Supported operators are:

### `target_distance`
Best alignment occurs at a specific numeric target on a documented scale.

`alignment = 1 - |attribute - target| / scale_span`, clipped to `[0,1]`.

Use for preferences such as wanting a moderate/specific level rather than simply more or less.

### `higher_preferred`
Higher values on the documented scale are preferred.

`alignment = (attribute - scale_min) / scale_span`, clipped to `[0,1]`.

### `lower_preferred`
Lower values on the documented scale are preferred.

`alignment = (scale_max - attribute) / scale_span`, clipped to `[0,1]`.

### `range`
Any value inside the explicit acceptable range receives alignment `1`. Values outside the range decline with distance using the documented scale span and are clipped to `[0,1]`.

This requires `target_min <= target_max`.

### `categorical_match`
Case-insensitive exact category match receives `1`; an observed nonmatching category receives `0`. Missing category evidence remains missing, not zero.

Categorical values are not converted into arbitrary numeric order.

## Scale compatibility

Numeric operators require valid documented `scale_min < scale_max`. `target_distance` requires a numeric target. `range` requires numeric range endpoints. Invalid or unsupported operator configurations fail validation rather than silently selecting another interpretation.

Alignment is a transparent compatibility measure, not a probability of satisfaction, success, placement, or persistence.

## Importance

Importance values are user-supplied/approved. The system does not invent importance weights for interests, skills, work values, or other attributes.

A pathway summary is the importance-weighted mean across observed explicit preferences. Coverage is reported separately.

## Missing evidence

Missing occupation-attribute evidence reduces `career_alignment_coverage_rate`. It does not become a mismatch score of zero. A high score with low coverage must remain distinguishable from a similarly high score with broad evidence coverage.

## No earnings dominance

Wages and employment growth remain separate labor-market dimensions. They are not silently incorporated into career-preference alignment. Explicit earnings/growth priorities should be represented separately and transparently.

## No deterministic career claim

CIP↔SOC establishes related pathways, not guaranteed outcomes. Alignment with an occupation does not establish that a program will place a student in that occupation or that the user will enjoy or succeed in it.

## Outputs

- `career_preference_alignment_detail.csv`: preference-by-pathway evidence, declared operator, and alignment
- `career_pathway_alignment.csv`: pathway-level score, evidence count, coverage, and status
- `career_preference_alignment_qa.json`: explicit preference count, operators used, pathway-row count, and semantic rule

## Program-level use

Program/candidate summaries retain multiple pathway perspectives: pathway breadth, median/range/dispersion of alignment, representative pathways, evidence coverage, and—only when a validated threshold is explicitly supplied—the number/share of strongly aligned pathways. Sheer pathway count is not a quality score, and one highly aligned occupation does not establish that the entire program is an excellent career match.

## Public-question activation gate

A plain-language career question is not automatically eligible for the public matcher merely because an O*NET-like attribute ID has been drafted. Questionnaire mappings marked `requires_attribute_mapping_review=true` must fail closed in the questionnaire mapper and remain absent from the public browser request. Activation requires explicit review of the source attribute, scale, operator semantics, and user-facing wording; skipping a pending question must never block career-first exploration.

## Validation requirements

Before production scoring, operator semantics must be regression-tested against synthetic fixtures and reviewed against the source domain's documented scale meaning. In particular, O*NET attributes must not be assigned `higher_preferred` or `lower_preferred` merely because their values are numerically ordered; the operator must correspond to an explicit user preference and a defensible interpretation of the source scale.
