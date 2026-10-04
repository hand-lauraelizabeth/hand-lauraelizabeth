# Transfer & Articulation Layer Specification

**Status:** implementation specification; authoritative-source research refreshed 2026-10-04  
**Project:** College + Career Matching Tool  
**Purpose:** add transferability and degree-applicability evidence without treating transfer as a binary institution-level attribute or assuming that a course accepted for credit necessarily advances a student's intended major.

## Why this layer is separate

Transfer is not one signal. The matcher should distinguish at least four questions:

1. **Can a student transfer from institution A to institution B?**
2. **Will a specific course receive credit?**
3. **Will that credit apply to general education, a major, a prerequisite, or electives?**
4. **Does a defined program-to-program pathway preserve progress toward the intended credential?**

The model must not collapse those questions into a single `transfer_friendly` score.

## Authoritative source hierarchy

| Priority | Source | Coverage | Model role | Notes |
| --- | --- | --- | --- | --- |
| 1 | SUNY Transfer Equivalency Platform (STEP): Transfer Agreement Inventory, Transfer Paths, Core Course Lookup, Course Equivalencies | SUNY system | Structured transfer agreements, guaranteed path/core-course evidence, course equivalencies | SUNY states that Transfer Path Core Courses are guaranteed to transfer into aligned path majors when policy conditions are met. Preserve path and course context. |
| 1 | CUNY Transfer Explorer (T-Rex) + CUNY Universal Transfer Path / articulation resources | CUNY system | Course equivalencies, program comparisons, major-path evidence, formal articulation context | T-Rex explicitly supports course-credit transfer and how credits apply to majors/minors. CUNY's 2026 articulation process adds standardized program/credit fields. |
| 2 | State/system articulation repositories and published institutional agreements | State/system or institution pairs | Expand beyond NY where structured authoritative data are available | Add adapters one system at a time; do not scrape arbitrary third-party transfer sites into the authoritative layer. |
| 3 | Institution-published transfer-credit policies and agreements | Institution | Policy/context fallback | Use as evidence with capture date and source URL; lower structural confidence than system-maintained equivalency/path data. |
| 4 | Federal consumer-information disclosures | National policy context | Availability/provenance support, not equivalency inference | Federal guidance supports public transfer/articulation information but does not provide a national course-equivalency database. |

## Initial implementation scope

Start with **New York public higher education** because both major systems expose current public transfer resources and because this yields a meaningful community-college → bachelor's pathway layer before attempting national heterogeneity.

### SUNY

Initial public components:

- Transfer Agreement Inventory
- SUNY Transfer Paths
- Transfer Path Core Course Lookup / planner
- public Course Equivalency lookup
- SUNY-wide course catalog where needed for course identity

The public Transfer Agreement Inventory exposes agreement-level fields including an agreement ID, initial campus, partner campus, agreement type, source program, destination, and source link/context. This is suitable for a first agreement-level adapter.

### CUNY

Initial public components:

- CUNY Transfer Explorer course-equivalency rules
- CUNY Program Comparison
- Universal Transfer Path evidence where published
- formal articulation agreements / 2026 standardized articulation fields

CUNY's current articulation guidance identifies useful structured concepts for the matcher, including sending/receiving institution, program/concentration, degree type, total major credits, credits transferring as major credit, and credits remaining for the bachelor's degree.

## Canonical tables

### `transfer_agreement`

One row per authoritative agreement/path relationship.

| Field | Type | Description |
| --- | --- | --- |
| `transfer_agreement_id` | string | Stable source ID when available; otherwise deterministic source-scoped ID |
| `source_system` | string | SUNY, CUNY, other authoritative system/state/institution |
| `sending_institution_source_id` | string | Source-system campus identifier |
| `receiving_institution_source_id` | string | Source-system campus identifier |
| `sending_unitid` | string nullable | Crosswalked IPEDS UNITID; never inferred from name alone without review/confidence rule |
| `receiving_unitid` | string nullable | Crosswalked IPEDS UNITID |
| `agreement_type` | string | articulation, dual admission, transfer path, universal transfer path, other |
| `sending_program_name` | string nullable | Source program label |
| `receiving_program_name` | string nullable | Destination program label |
| `sending_cip` | string nullable | CIP only when source or validated program crosswalk supports it |
| `receiving_cip` | string nullable | CIP only when source or validated program crosswalk supports it |
| `sending_degree` | string nullable | AA/AS/AAS/etc. |
| `receiving_degree` | string nullable | BA/BS/BBA/etc. |
| `guarantee_type` | string nullable | What is actually guaranteed: admission, course credit, major applicability, junior standing, etc. |
| `minimum_grade` | string nullable | Preserve source condition, e.g. C or better |
| `effective_start` | date nullable | Source effective date |
| `effective_end` | date nullable | Source expiration/end date |
| `source_url` | string | Authoritative source |
| `retrieved_at` | datetime | Snapshot retrieval time |
| `source_version` | string nullable | Published update/version label |
| `evidence_status` | string | current, historical, pending-review, superseded |

### `course_equivalency`

One row per sending-course → receiving-course/rule relationship.

| Field | Type | Description |
| --- | --- | --- |
| `equivalency_id` | string | Stable/deterministic relationship ID |
| `sending_unitid` | string nullable | Sending institution |
| `receiving_unitid` | string nullable | Receiving institution |
| `sending_course_code` | string | Source course code |
| `sending_course_title` | string nullable | Source title |
| `receiving_course_code` | string nullable | Destination course code; nullable for elective/block credit |
| `receiving_course_title` | string nullable | Destination title |
| `credit_value` | number nullable | Credit amount when stated |
| `applicability` | string nullable | major, gen-ed, prerequisite, elective, unspecified |
| `major_or_path` | string nullable | Program/path context when rule is conditional |
| `minimum_grade` | string nullable | Grade condition |
| `rule_notes` | string nullable | Conditions/exceptions |
| `source_url` | string | Authoritative source |
| `retrieved_at` | datetime | Snapshot retrieval time |
| `evidence_status` | string | current, historical, pending-review, superseded |

### `transfer_path`

One row per system-defined academic transfer path.

| Field | Type | Description |
| --- | --- | --- |
| `transfer_path_id` | string | Source path identifier |
| `source_system` | string | SUNY/CUNY/etc. |
| `path_name` | string | Discipline/path name |
| `cip` | string nullable | Validated CIP mapping, not title-only assumption |
| `policy_guarantee` | string | Plain-language guarantee from source policy |
| `required_credits` | number nullable | If explicitly stated |
| `source_url` | string | Authoritative path source |
| `retrieved_at` | datetime | Snapshot retrieval time |

### `transfer_path_course`

Bridge between a transfer path and its required/core courses.

- `transfer_path_id`
- `institution_source_id`
- `unitid` nullable
- `course_code`
- `course_title` nullable
- `core_requirement_label`
- `minimum_grade` nullable
- `source_url`
- `retrieved_at`

## Institution identity crosswalk

Transfer sources often use campus names or system-specific identifiers rather than UNITID. Use the existing institution-identity review architecture:

1. exact authoritative identifiers where available;
2. exact normalized name + state only as a candidate;
3. address/domain/system membership as corroborating evidence;
4. unresolved cases remain unresolved and visible;
5. never merge campuses solely because names are similar.

Add transfer-specific identity fields to the review output so a missing UNITID does not delete an otherwise valid transfer record.

## Program identity and CIP mapping

Program names in articulation agreements are not automatically CIP codes.

Mapping order:

1. source-published CIP;
2. institution program inventory exact identifier/CIP match;
3. reviewed program-name + award-level crosswalk;
4. unresolved.

Store mapping method and confidence. Preserve the source program text in all cases.

## Transfer evidence hierarchy

For user-facing explanations, rank evidence by specificity rather than forcing it into one score:

1. **Course + destination program applicability** — strongest evidence.
2. **Course equivalency** — credit relationship known, applicability may still be unknown.
3. **Program-to-program articulation / transfer path** — pathway evidence, but individual transcript conditions may apply.
4. **Systemwide transfer policy** — useful policy context, not proof for a specific course/program.
5. **Institutional policy only** — lowest structured confidence.

## Recommendation features

Keep these separate and explainable:

- `has_program_articulation`
- `has_course_equivalency_evidence`
- `has_major_applicability_evidence`
- `guaranteed_path_flag`
- `junior_standing_policy_flag`
- `estimated_credits_applicable` only when source evidence supports calculation
- `transfer_evidence_specificity`
- `transfer_evidence_recency`
- `transfer_conditions_present`
- `transfer_data_coverage_status`

Do **not** create a universal transfer score until validation demonstrates that a composite adds value without hiding material conditions.

## QA gates

### Source QA

- authoritative domain/source only for the production evidence layer;
- snapshot retrieval date present;
- source record count recorded;
- stable/deterministic record IDs unique;
- no silent overwrite of prior snapshots.

### Join QA

- report UNITID match rate separately for sending and receiving institutions;
- preserve unmatched institutions for review;
- report program/CIP mapping coverage separately from institution coverage;
- no many-to-many collapse;
- no course-equivalency record dropped solely because applicability is unknown.

### Semantic QA

- `credit accepted` must not be rewritten as `applies to major` unless source says so;
- `articulation agreement` must not be rewritten as guaranteed admission unless source says so;
- system policy must not be presented as a transcript-level determination;
- expired/superseded agreements remain historical, not current recommendations;
- transfer-path guarantees retain minimum-grade and other published conditions.

### Regression gates

Once a first snapshot is ingested, establish floors for:

- agreement count;
- distinct sending institutions;
- distinct receiving institutions;
- transfer paths;
- course-equivalency records;
- UNITID match rate;
- program/CIP mapping rate;
- records with explicit applicability;
- records with conditions/notes preserved.

A large unexplained drop fails the build.

## User-facing explanation contract

A recommendation involving transfer should answer:

- **What evidence exists?** Agreement, path, or course equivalency.
- **Between which institutions/programs?** Preserve exact source labels.
- **What is guaranteed?** Credit, applicability, standing, admission, or another stated benefit.
- **What conditions apply?** Grade, course, program, timing, or policy conditions.
- **How current is the evidence?** Source/update/retrieval date.
- **What is not known?** Explicitly state when degree applicability or transcript-level determination is unavailable.

Example:

> SUNY publishes a Transfer Path covering this discipline and identifies core courses intended to transfer into aligned majors, subject to the path's published conditions. This is stronger evidence than a general transfer policy, but it is not a transcript evaluation. Review the linked current source with an advisor before enrollment decisions.

## Implementation sequence

1. **SUNY agreement adapter** — ingest the public Transfer Agreement Inventory into `transfer_agreement`; preserve source IDs and URLs.
2. **SUNY path adapter** — normalize Transfer Paths and core-course relationships.
3. **Institution crosswalk** — map SUNY campus identities to IPEDS UNITID with review output.
4. **CUNY equivalency adapter** — ingest/normalize public T-Rex course-equivalency relationships where technically and legally accessible.
5. **CUNY program/path layer** — add Program Comparison / UTP / articulation evidence with applicability semantics.
6. **Integrated pathway join** — institution → program → transfer evidence → CIP/SOC → occupation/labor-market evidence.
7. **Coverage and regression report** — establish baseline counts and missingness.
8. **Only then** expose transfer signals to recommendation calibration.

## Explicit non-goals for this phase

- predicting whether a registrar will accept an individual student's credits;
- treating transfer as a guarantee of admission unless the source explicitly says so;
- estimating credits saved from weak or institution-level policy evidence;
- scraping proprietary third-party equivalency databases as a hidden dependency;
- collapsing transfer, affordability, admissions, and career alignment into one opaque rank.

## Next executable task

Implement the SUNY Transfer Agreement Inventory adapter first. It is a bounded, authoritative public source with explicit agreement-level records and gives the matcher a concrete transfer layer while course-level adapters are developed separately.