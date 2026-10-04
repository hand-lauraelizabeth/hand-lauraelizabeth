# SUNY Transfer Path ↔ Core Course Bridge

**Status:** adapter implemented; authoritative full-snapshot execution pending  
**Source:** SUNY STEP Transfer Paths, Transfer Path Planner, and Core Course Master List

## Purpose

Replace fragile title-only joins between Transfer Path Planner rows and SUNY Core Courses with stable STEP identifiers wherever the source exposes them, while preserving unresolved/ambiguous rows for review.

SUNY states that Core Courses fulfill lower-level requirements and apply to aligned Transfer Path majors; the transfer guarantee is path-specific and generally conditioned on completion with a C or better. The bridge therefore retains `pathid` and Core Course identity together rather than treating a Core Course as a universal major requirement outside its path context.

## Current authoritative structures verified 2026-10-04

### Core Course Master List

STEP publishes a real-time master list with:

- Course ID (`csid`/`course_id`)
- Course title
- Active flag
- URL key
- Universal Code when assigned

This is the preferred Core Course identity source.

### Core Course Navigator

Individual `csid` pages expose the Core Course title, description where present, Universal Code where assigned, and campus-course mappings. Examples demonstrate that a Core Course can map to one local course, multiple alternatives, or an AND combination.

### Transfer Path Planner

Planner pages expose a `pathid`, a campus/source institution parameter (`pathinst`), Core Course labels, local equivalent-course expressions, and explicit `No Course Identified` gaps. The bridge links planner Core Course labels to the master-list identity without rewriting the local expression.

## Join order

1. explicit `csid`/Core Course ID when captured from source markup;
2. otherwise exact normalized Core Course title against the master list;
3. duplicate normalized titles → review, never arbitrary selection;
4. no exact match → unresolved, preserving the planner text.

No fuzzy automatic match is permitted in the production bridge.

## Output

`transfer_path_core_course.csv` contains:

- deterministic bridge ID;
- `pathid`;
- `pathinst`;
- exact planner Core Course label;
- stable Core Course ID when matched;
- canonical Core Course title;
- Universal Code;
- active status;
- match method/status;
- exact equivalent-course expression;
- source URL;
- review note.

Separate review and coverage outputs are generated.

## Why Universal Code is not the primary key

Universal Codes are useful semantic labels but are not sufficiently unique/stable to replace STEP's Core Course ID. Current source examples include broad codes such as `MAT0`, `PHY0`, `ART0`, `CSC0`, while some master-list rows have blank Universal Codes. The bridge therefore uses the source Course ID as the identity key and retains Universal Code as an attribute.

## Expression preservation

Do not flatten:

- `A or B` into two independent required courses;
- `(A and B) or C` into three independent equivalents;
- `No Course Identified` into a negative claim about program availability.

A later expression parser may produce normalized AND/OR groups, but the raw source expression remains authoritative and auditable.

## QA

The adapter fails on:

- empty Core Course master input;
- empty planner input;
- missing `pathid`;
- duplicate deterministic bridge IDs;
- a row marked matched without a stable Core Course ID.

Coverage output reports matched/review/unresolved rows plus distinct paths and Core Course IDs. Regression floors are established only after the full authoritative snapshot is executed.

## Current source spot checks

Verified source examples include:

- `csid=203`: Calculus-based Physics I: Mechanics with Lab, Universal Code `MAT0`, with campus mappings;
- `csid=22`: College Algebra, Universal Code `MAT102`;
- `csid=24`: Composition I, Universal Code `ELT101`;
- `csid=40`: General Physics II, Universal Code `PHY102`, including AND course combinations at some campuses;
- `csid=207`: Conventions of the Discipline, Universal Code `ELT0`, with multiple qualifying courses at several campuses.

These examples demonstrate why stable Course ID + path context + local expression must all be retained.

## Next step

Capture the full Core Course Master List and Transfer Path Planner snapshots, run the bridge, establish the first match/coverage baseline, then join accepted campus UNITIDs. After that, begin the CUNY Transfer Explorer adapter so the transfer layer is not SUNY-only.
