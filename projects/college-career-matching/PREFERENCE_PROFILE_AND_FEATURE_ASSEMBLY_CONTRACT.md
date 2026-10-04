# Preference Profile & Candidate Feature Assembly Contract

**Status:** executable profile governance and grain-safe feature assembly implemented.

## Purpose

Translate what a user actually says they need or prefer into structured inputs, then assemble the evidence needed to compare eligible institution × program candidates. The system must not manufacture preferences to fill an incomplete profile.

## Profile contract

Each profile row contains:

- `preference_id`
- `dimension`
- `value`
- `mode`: `preference`, `hard_constraint`, or `context`
- `priority_explicit`: whether the user explicitly supplied/approved this priority

Only rows with `priority_explicit=true` may influence model features, constraints, or weighting. Inactive rows can remain in the profile for audit/UI purposes but are exported separately.

### No hidden defaults

If a user does not state a preference for institution size, sector, prestige/selectivity, modality, geography, earnings, campus setting, or another dimension, the model must not assume one.

Product-level defaults required for operation (for example, display count) are not user preferences and must be documented separately.

## Hard constraint vs preference vs context

- **hard constraint**: an explicit eligibility boundary; passed to the candidate constraint engine.
- **preference**: affects comparison only after candidate eligibility is established.
- **context**: information used to interpret evidence or generate appropriate variants, but not automatically scored.

A preference must never become a hard constraint solely because its weight is high.

## Feature assembly grains

Evidence sources declare their join grain in a manifest. Supported initial grains:

- `institution`: `UNITID`
- `program`: `UNITID + program_id`
- `candidate`: `candidate_id`
- `transfer_path`: `UNITID + program_id + transfer_path_id`

Every evidence table must be unique at its declared grain. A join that would multiply candidates fails. A join that would overwrite an existing non-key column fails. This prevents silent many-to-many contamination.

## Evidence families

The assembler is designed to receive normalized upstream tables for:

- institution identity/characteristics/accreditation
- program/CIP evidence
- affordability and College Scorecard outcomes
- transfer/articulation/path applicability
- CIP↔SOC career pathways
- O*NET occupation/skill evidence
- BLS projections
- current OEWS national/state/local labor-market evidence
- geography
- later permitted observed outcome/employer evidence

Not every source applies to every candidate. Missing joins remain missing evidence and are handled by the pre-score evidence audit rather than filled with zero.

## Geography

Geographic evidence is contextual. The architecture should eventually support distinct markets:

- institution-local labor market
- user's home/commuting market when explicitly supplied
- intended destination market
- remote/national market
- other user-selected labor markets

These should not be collapsed into one implicit geography preference.

## Career pathways

Program→career evidence remains many-to-many. A program may map to multiple occupations through CIP↔SOC and occupations may be supported by multiple programs. The assembler must preserve pathway identity rather than averaging occupations into an unexplained program value upstream.

## Transfer

Transfer-path features are only joined at transfer-path grain when a validated variant exists. Generic institution transfer policy must not masquerade as course/program applicability.

## Outputs

- `model_ready_candidate_features.csv`
- `active_preference_profile.csv`
- `inactive_unspecified_profile_rows.csv`
- `candidate_feature_join_log.csv`
- `candidate_feature_assembly_summary.json`

The model-ready table then passes through evidence audit, dimension normalization, scenario/sensitivity testing, coverage/fairness diagnostics, and explanation QA.

## Next implementation block

Build the **program-to-career pathway aggregator**. The existing CIP↔SOC relation is intentionally many-to-many; the recommendation layer now needs a transparent way to summarize occupation-level projections, wages, local evidence, and O*NET characteristics into program/candidate features without hiding pathway breadth, cherry-picking the highest-paid occupation, or treating absent/suppressed local evidence as zero.
