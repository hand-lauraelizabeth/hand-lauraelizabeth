# CUNY Transfer Explorer (T-Rex) Adapter Specification

**Status:** adapter implemented; authoritative snapshot execution pending  
**Reviewed:** 2026-10-04

## Role in the matching model

CUNY Transfer Explorer supplies a second authoritative New York public-system transfer layer alongside SUNY STEP. It supports evidence at several distinct levels:

1. directional CUNY-to-CUNY course equivalency;
2. non-CUNY course/training/exam evaluation into CUNY;
3. degree/major applicability;
4. program entry requirements;
5. transfer plans/pathway context.

These are not collapsed into one transfer score.

## Current authoritative behavior

The public T-Rex interface states that it is updated daily from CUNY official source systems. Course pages use stable numeric identifiers in URLs and can show how one selected course transfers across the CUNY system. T-Rex explicitly warns that equivalency can vary based on combinations of courses.

The public subject workflow requires a directional relationship: one sending college to one or more receiving colleges, or one receiving college to one or more sending colleges.

## Canonical course-equivalency record

`cuny_transfer_explorer_adapter.py` normalizes observed rules into:

- deterministic `equivalency_id`;
- `source_system = CUNY_TREX`;
- T-Rex source course ID;
- sending institution label + later UNITID;
- sending subject/code/title/credits;
- receiving institution label + later UNITID;
- receiving course expression/title/credits;
- expression type;
- applicability tags;
- minimum-grade/rule notes;
- source URL and retrieval timestamp;
- evidence status.

## Compound-rule semantics

T-Rex can display equivalencies that depend on combinations of courses. The adapter therefore classifies receiving expressions as:

- `single_course`;
- `and_combination`;
- `or_alternatives`;
- `compound_boolean`;
- `unresolved`.

Do not split an AND combination into independent equivalencies. Do not select one OR branch as the canonical equivalent. Preserve the source expression until a structured rule parser can represent its Boolean logic losslessly.

## Applicability is separate from equivalency

T-Rex course records can expose tags such as:

- Required Core;
- Flexible Core;
- Major Gateway;
- Universal Transfer.

The adapter stores these separately. A course transferring for credit does not by itself prove that it applies to a student's intended major.

The `Map Credits to CUNY Major Requirements` feature provides stronger major-applicability evidence and should populate the separate program/applicability layer. It currently focuses on majors at CUNY bachelor's-degree colleges and explicitly distinguishes major requirements from common core/other degree requirements.

## Missing evaluation semantics

For non-CUNY coursework, T-Rex states that absence of a listed evaluation does **not** imply that the receiving college will reject the course; unevaluated coursework can be considered upon admission. Therefore:

- missing rule ≠ non-transferable;
- missing rule → `not_pre_evaluated` / unknown evidence state;
- recommendation explanations must not turn missing data into a negative transfer claim.

## Institution identity

Reuse the conservative institution-identity principles established for SUNY:

1. source-system identifier where available;
2. exact authoritative identity;
3. reviewed alias/corroborated match;
4. unresolved remains unresolved.

CUNY schools/colleges must map to the correct IPEDS reporting unit; school/subunit context must not be silently merged into a different institution.

## Program evidence

The major-requirement layer should retain:

- receiving CUNY college;
- plan/major;
- sub-plan/track where present;
- source learning experience/course;
- receiving course/equivalency;
- requirement/application category;
- observed progress/applicability only when the source explicitly supports it;
- source URL/retrieval metadata.

No inferred CIP should be attached until the CUNY program is crosswalked to the existing IPEDS/CIP program universe.

## Current 2026 governance context

CUNY states that its Equivalency Review Module (ERM), first launched in 2022, becomes the required and exclusive mechanism in Fall 2026 for initiating, reviewing, approving, and documenting course-equivalency changes. This strengthens T-Rex's role as current operational evidence, but does not eliminate the need to snapshot/version public observations because rules can change.

CUNY's 2026–27 Transfer Initiative also calls for stronger Universal Transfer Path implementation, improved degree applicability, university-level course-equivalency review requirements, UTP-based transfer maps, and standardized articulation-agreement processes. These are separate evidence families to add after the base course-equivalency layer.

## QA gates

Fail normalization if:

- zero records are observed;
- a stable source course ID is absent;
- sending or receiving institution is absent;
- deterministic IDs collide.

Report separately:

- distinct sending/receiving institutions;
- expression-type distribution;
- missing grade/rule metadata;
- institution identity match rate;
- major-applicability coverage;
- records with Universal Transfer/Major Gateway/Core tags;
- unresolved compound expressions.

Coverage regression floors must be based on observed authoritative snapshots, not guessed before ingestion.

## Implementation sequence

1. **Implemented:** directional course-equivalency normalizer.
2. Capture/version an authoritative public T-Rex snapshot and establish coverage baseline.
3. Build CUNY institution → UNITID identity table.
4. Normalize major-applicability evidence from Map Credits to Major Requirements.
5. Add non-CUNY/CPL evidence with explicit `not_pre_evaluated` semantics.
6. Add Universal Transfer Path / articulation evidence.
7. Crosswalk validated CUNY programs to CIP.
8. Join transfer evidence to the existing program → occupation pathway without collapsing transfer, major applicability, and career fit into one signal.
