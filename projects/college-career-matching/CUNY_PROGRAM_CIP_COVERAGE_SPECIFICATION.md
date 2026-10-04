# CUNY Program → CIP and Program Requirements Coverage

Status: adapter implemented; authoritative inventory execution and full T-Rex program baseline pending.

## Why this layer exists

T-Rex plan/sub-plan identifiers describe Degree Works program structures. CIP is a federal subject taxonomy. Similar titles are not sufficient evidence that a T-Rex plan has a particular CIP. The crosswalk therefore uses authoritative registered-program identity before attaching CIP.

CUNY states that New York's IRP code uniquely identifies an individual registered program, while CIP classifies programs by subject area. This distinction is preserved in the model.

## Source hierarchy

1. Current CUNY/NYSED registered academic-program evidence containing program identity and CIP.
2. T-Rex program/plan/sub-plan identifiers and Degree Works requirement structures.
3. IPEDS completions/program inventory as corroboration and coverage evidence, not a title-only identity resolver.

Historical CUNY Academic Programs Inventory reports can be used to understand schema and historical identity, but must not be treated as the current program universe without a current-source check.

## Canonical crosswalk

`cuny_program_cip_adapter.py` emits:

- `program_crosswalk_id`
- `trex_college`
- `trex_program_name`
- `trex_award`
- `trex_program_id`
- `registered_program_id`
- `cip_code`
- `hegis_code`
- `match_method`
- `match_status`
- `candidate_count`
- `review_note`

Only a unique authoritative registered-program ID match is auto-accepted. Title similarity is never sufficient for automatic CIP assignment.

## Program Requirements coverage

Coverage must be measured independently from program identity. T-Rex currently states that its Program Requirements / Map-to-Major major tools cover bachelor's-degree-awarding CUNY colleges, while Program Comparison covers only selected major families. Therefore the model tracks at least:

- `program_identity_covered`
- `registered_program_cip_covered`
- `trex_program_requirements_covered`
- `trex_map_to_major_covered`
- `trex_program_comparison_covered`
- `requirement_structure_complete_status`
- `coverage_observed_at`

A program can have an authoritative CIP but no T-Rex requirement representation, or T-Rex requirements but an unresolved CIP crosswalk. Neither condition deletes the program.

## Temporal semantics

T-Rex Program Requirements pages state that the displayed Degree Works blocks are current-state representations and do not provide history. Snapshot date is therefore required for every extracted requirement structure. Historical change must be reconstructed from our own versioned snapshots rather than inferred from the live page.

## Requirement semantics

Keep separate:

1. registered program identity and CIP;
2. T-Rex plan/sub-plan identity;
3. required major credits;
4. minimum major GPA;
5. major residency credits;
6. requirement blocks and AND/OR alternatives;
7. course equivalencies;
8. course applicability to a target major;
9. Pathways/Common Core and other degree requirements.

Do not turn any one of these into a claim about the others without evidence.

## QA gates

- Accepted crosswalk rows require a CIP.
- Multiple registered-program candidates remain review rows.
- No title-only automatic CIP assignment.
- T-Rex programs missing a CIP remain in the universe.
- Registered programs absent from T-Rex remain in the college/program universe.
- Program Requirements coverage is never generalized from a single sampled program.
- Snapshot date/source is required before establishing a regression floor.
- Requirement blocks marked incomplete or under active T-Rex development remain explicitly incomplete.

## First execution baseline

The first authoritative run should report:

- distinct T-Rex colleges represented in Program Requirements;
- distinct T-Rex plans and sub-plans;
- programs with authoritative registered-program/CIP matches;
- review/unresolved program identities;
- programs with requirement blocks;
- programs with major-credit, GPA, and residency metadata;
- programs/pages flagged incomplete;
- coverage by college and award level.

Do not invent a target match rate before the first authoritative run.

## Downstream join

Once accepted, the chain is:

`T-Rex program → registered program → CIP → official CIP↔SOC crosswalk → occupation → O*NET/BLS`

Transfer applicability remains an independent evidence path:

`sending course(s) → equivalency → receiving course → T-Rex program requirement → accepted program/CIP identity`

This allows career alignment and transfer efficiency to reinforce an explanation without collapsing them into the same signal.
