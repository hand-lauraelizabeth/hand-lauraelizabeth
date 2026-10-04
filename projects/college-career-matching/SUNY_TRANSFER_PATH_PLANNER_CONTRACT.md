# SUNY Transfer Path Planner Evidence Contract

**Status:** adapter implemented; full source-universe capture pending  
**Updated:** 2026-10-04

## What the live source adds

SUNY STEP's current Transfer Path Planner exposes a path × campus view with explicit URL identifiers:

- `pathid` — Transfer Path identifier;
- `pathinst` — campus/institution identifier used by STEP;
- campus label;
- Transfer Path name;
- Core Course;
- equivalent campus course expression;
- notes/context when present.

This gives the matching tool a stronger bridge than institution-level transfer policy alone: it can preserve evidence that a particular campus course fulfills a particular SUNY Core Course in the context of a named Transfer Path.

SUNY states that Core Courses transfer in programs aligned with the relevant Transfer Path when completed with a C or better, and that Core Courses fulfill lower-level requirements for aligned path majors. That policy context must remain attached to the planner evidence rather than being generalized to every major.

## Observed live examples used to harden the model

The current public pages demonstrate several structures the adapter must preserve:

1. **One local course** — e.g., a Core Course maps to one campus course.
2. **OR alternatives** — one Core Course may be satisfied by multiple alternative local courses.
3. **AND combinations** — a mapping can require a course combination, not one interchangeable course.
4. **No Course Identified** — the campus/path/core-course combination exists but STEP currently identifies no qualifying local course.
5. **Same Core Course, different campuses** — local course identity varies by institution.

These are semantic differences, not formatting noise.

## Canonical outputs

### `suny_transfer_path_plan.csv`

One row per path × campus × Core Course observation.

Key fields:

- `path_plan_row_id`
- `path_id`
- `pathinst`
- `campus_name_source`
- `path_name_source`
- `core_course_source`
- `campus_course_expression`
- `course_identified_flag`
- `notes`
- `source_url`
- `retrieved_at`

### `suny_transfer_path_course_option.csv`

A child table for alternatives. Explicit `or` alternatives become separate options. Expressions containing `and` remain intact and receive `combination_required_flag=1`.

This prevents `(BIO1550 and BIO.10)` from being incorrectly represented as two interchangeable courses.

### `suny_transfer_path_plan_qa.csv`

Records:

- planner rows;
- unique deterministic rows;
- option rows;
- `No Course Identified` rows;
- multi-option rows;
- combination-required option rows;
- deterministic-ID uniqueness.

## Join strategy

`pathinst` is preserved as a STEP source identifier. It should be added to the SUNY campus identity universe and resolved to UNITID using the existing conservative SUNY→IPEDS identity layer.

Join sequence:

`STEP pathinst` → reviewed campus identity → `UNITID` → institution/program backbone

and independently:

`path_id` + Core Course → Transfer Path/Core Course bridge → program/path evidence.

The two joins must report coverage separately.

## Missing-course semantics

`No Course Identified` means only that the current planner page does not identify a campus course for that Core Course/path combination. It does **not** mean:

- the institution lacks the subject entirely;
- a student can never satisfy the requirement;
- the Transfer Path is invalid;
- another course cannot transfer after individual review.

For matching, this becomes a transparent coverage/gap signal and may support a warning to verify options with the institution/advisor.

## Recommendation features enabled

Once coverage is sufficient, derive explainable features such as:

- `path_course_coverage_rate` — identified Core Course mappings / displayed Core Course requirements for a campus/path;
- `path_missing_core_course_count`;
- `path_multi_option_count`;
- `path_combination_requirement_count`;
- `path_evidence_recency`;
- `pathinst_identity_status`.

Do not convert these directly into a universal ranking weight before validation. They first belong in the explanation and pathway-feasibility layers.

## QA gates

- required source columns present;
- nonzero planner rows;
- deterministic row IDs unique;
- every option has a parent planner row;
- `No Course Identified` never appears as a course option;
- AND combinations are not split into OR alternatives;
- source URL retained for every row;
- `path_id` and `pathinst` retained exactly as source identifiers.

After a complete source-universe capture, establish empirical regression floors for path count, campus count, path × campus combinations, Core Course observations, and mapping coverage. Do not guess these floors in advance.

## Next backlog step

Build the **Transfer Path ↔ Core Course bridge** and a path/campus coverage report. The live planner already supplies `path_id` and Core Course labels, while the Core Course Navigator supplies stable `csid`/Universal Code evidence. The bridge should resolve these with explicit source evidence and keep unresolved label mappings visible for review.