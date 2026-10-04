# SUNY Transfer Paths Implementation Contract

**Status:** adapter implemented; authoritative snapshot execution pending  
**Reviewed:** 2026-10-04

## Current authoritative semantics

SUNY's current Transfer Paths materials distinguish:

- a **Transfer Path**: a discipline-level pathway containing common lower-division requirements;
- a **Core Course**: a universal course definition used in one or more paths;
- a **campus course mapping**: the local SUNY course or courses approved for a Core Course;
- a **path-aligned major/program**: the destination context in which the transfer guarantee applies.

Current SUNY guidance states that approved Transfer Path Core Courses completed with a grade of C or better are guaranteed to transfer for applicable major and/or required cognate requirements, rather than merely as elective credit. Some programs can require a higher grade when that requirement also applies to native students. Pass/fail treatment is discretionary.

This guarantee must remain attached to its **aligned path/major context**. A Core Course record alone is not a claim that the course satisfies every SUNY major.

## Implemented adapter

`suny_transfer_paths_adapter.py` consumes locally captured authoritative snapshots and produces:

- `transfer_path.csv`
- `core_course.csv`
- `transfer_path_course.csv`
- `transfer_path_qa.json`

The adapter intentionally does not scrape SUNY pages during a build. A source snapshot, retrieval timestamp, and authoritative source URL are explicit inputs.

## Core Course identity

SUNY exposes a Core Course name and, where available, a Universal Code. The adapter creates a deterministic `core_course_id` from those source values while preserving both fields.

Do not infer a CIP code from a Universal Code. They are separate taxonomies.

## Campus-course mapping

The current Core Course Navigator can expose one or multiple campus courses for a universal Core Course. The mapping layer therefore remains many-to-many.

Examples visible in the current public navigator include:

- Composition I / Universal Code `ELT101`, with different approved local course codes across campuses;
- Conventions of the Discipline / `ELT0`, where a single campus can expose multiple approved courses;
- some Core Courses represented by paired local courses or course + lab combinations.

Do not split a source value such as `BIO201 and BIO211` into independent guarantees unless SUNY's source structure explicitly identifies them as independent alternatives. Preserve the source expression when uncertain.

## Institution identity

The campus mapping initially preserves SUNY's campus label in `institution_source_id` and leaves `unitid` null. A separate identity adapter should map campus labels to IPEDS UNITID using the project's existing identity-review rules.

Required coverage report after the first snapshot:

- distinct SUNY campus labels;
- exact authoritative UNITID matches;
- reviewed/alias matches;
- unresolved campuses;
- match rate;
- any one-to-many or many-to-one identity conflicts.

No campus mapping is dropped because UNITID is unresolved.

## Path ↔ Core Course relationship

The first adapter normalizes path and Core Course source snapshots independently. A subsequent bridge should create `transfer_path_core_course` with:

- `transfer_path_id`
- `core_course_id`
- `requirement_type` (major, cognate, elective/choice, other source-defined category)
- `required_or_choice`
- `sequence_or_group` where published
- `source_url`
- `retrieved_at`

This bridge must be source-derived. Do not join a Core Course to a path merely because the course's discipline resembles the path title.

## QA gates

After a real snapshot is captured, fail or flag the build when:

1. path IDs are not unique;
2. Core Course IDs are not unique;
3. campus-course rows contain no campus or course expression;
4. duplicate campus/Core Course/course-expression rows appear unexpectedly;
5. a prior snapshot's path/core/mapping count drops materially without an explained source change;
6. the UNITID match rate drops below the established baseline;
7. a guarantee is emitted without the applicable path/major context;
8. a source condition such as minimum grade or multi-course requirement is silently discarded.

## User-facing matching features enabled by this layer

Once the path bridge and institution crosswalk are live, the matcher can expose separate evidence such as:

- student program has a SUNY Transfer Path;
- selected sending campus offers approved Core Courses for that path;
- selected Core Course has a local sending-campus equivalent;
- Core Course carries SUNY's major/cognate transfer guarantee subject to published conditions;
- path/course evidence date and source;
- unresolved destination-specific questions that still require advising or transcript evaluation.

This evidence should strengthen explanations, not become an opaque universal transfer score.

## Next executable task

Capture/export the current SUNY Transfer Path and Core Course datasets from the authoritative reporting/navigation surfaces, run them through the adapter, and establish the first path/core/campus coverage baseline. Then implement the campus-label → IPEDS UNITID crosswalk and the source-derived path ↔ Core Course bridge.
