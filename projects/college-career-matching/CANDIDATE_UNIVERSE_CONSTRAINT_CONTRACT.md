# Candidate Universe & Constraint Contract

**Status:** executable candidate construction and hard-constraint evaluation implemented.

## Candidate grain

The default candidate is an **institution × program** pair. A transfer-path variant is a distinct candidate only when an authoritative path/articulation record creates a materially different route for the student's sending context.

This prevents institution-level attributes from standing in for program availability and prevents one transfer agreement from being generalized to every student/program combination.

## Inputs

### Institution table
Required: `UNITID`, unique.

### Program table
Required: `UNITID`, `program_id`, unique as a pair. `program_id` should be an authoritative inventory/program identity where available; CIP alone is not necessarily a unique institution-program identity.

### Optional transfer-path table
Required: `UNITID`, `program_id`, `transfer_path_id`, unique as a triple. Only validated/material variants belong here.

### Constraint manifest
Required:

- `constraint_id`
- `field`
- `operator`
- `target`
- `unknown_policy`

Supported operators: `eq`, `neq`, `in`, `not_in`, `gte`, `gt`, `lte`, `lt`, `not_applicable`.

## Four-state constraint logic

Every constraint is evaluated as:

- `pass`
- `fail`
- `unknown`
- `not_applicable`

Unknown is not fail. A missing, suppressed, unresolved, not-pre-evaluated, or uncovered source value must not silently exclude a candidate.

The manifest makes the treatment of unknown evidence explicit. Recommended policies are:

- `keep`: retain as eligible-with-unknown
- `review`: retain but route for review
- `exclude`: exclude only where the product decision explicitly requires verified evidence and that rule has been justified

## Candidate dispositions

- `eligible`: all applicable hard constraints pass
- `eligible_with_unknown`: no failures, but at least one unknown retained
- `review`: no failure, but an unknown requires review
- `excluded`: at least one observed constraint failure
- `excluded_unknown_by_explicit_policy`: exclusion occurs because a declared policy requires verified evidence

The distinction between the two exclusion states is important for coverage/fairness auditing.

## Exclusion lineage

Excluded candidates are not deleted. Outputs preserve candidate IDs and per-constraint statuses so the system can answer:

- what was excluded?
- by which constraint?
- was exclusion based on observed evidence or unavailable evidence?
- did a data-source coverage gap change the candidate set?

## Hard constraints vs preferences

A hard constraint is a user/product eligibility requirement, not merely a desirable characteristic. Examples may include an explicitly required award level or program availability. Preferences such as lower cost, stronger local demand, smaller distance, or transfer convenience generally belong in the later comparison layer unless the user explicitly converts them into a hard limit.

The system must not infer hard constraints from ranking weights.

## Transfer handling

The ordinary institution-program candidate remains available even when transfer-path variants exist unless the user's search context specifically requires transfer eligibility. A path variant should preserve sending institution/system, destination program, agreement/path ID, conditions, and evidence specificity upstream.

No transfer path should be created from institution-name similarity or generic policy language.

## Outputs

- `candidate_universe_evaluated.csv`
- `candidate_constraint_detail.csv`
- `candidate_universe_summary.json`

The evaluated universe feeds the pre-score evidence audit and dimension normalizer. Only eligible/review-appropriate candidates should enter a scoring experiment; excluded records remain available for audit.

## Next implementation block

Build the **preference/profile contract and candidate feature assembler**. It should translate explicit user priorities into structured preference dimensions without turning unspecified preferences into defaults, join institution/program/transfer/career/local-labor evidence at the correct grain, and produce the model-ready candidate table consumed by the existing normalization, audit, sensitivity, fairness, and explanation layers.
