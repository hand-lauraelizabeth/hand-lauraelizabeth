# CUNY Course → Major Applicability Layer

**Status:** adapter implemented; authoritative snapshot execution and coverage baseline pending  
**Source:** CUNY Transfer Explorer (T-Rex)

## Purpose

Model the distinction between **receiving course equivalency** and **how that course applies to a particular receiving major/program**.

This is essential for transfer recommendations. A course can transfer to CUNY but still differ in whether it satisfies a major requirement, prerequisite, Required Core/Flexible Core requirement, elective, or another degree requirement.

## Current source semantics verified

T-Rex receiving-course pages expose course attributes such as:

- Major Gateway, sometimes for multiple disciplines;
- Universal Transfer for named disciplines;
- Pathways Required Core/Flexible Core categories;
- regular liberal-arts/non-liberal-arts classification;
- prerequisites and grade requirements;
- AND combinations where multiple sending courses are needed for a receiving equivalency.

These attributes are not interchangeable. In particular, `Major Gateway - CIS` is not proof that the course satisfies every CIS program's same requirement.

T-Rex Program Requirements pages provide the program-specific layer. They organize requirements into blocks and may express alternatives (`OR`), course combinations, credit requirements, minimum-grade conditions, and residency constraints. T-Rex itself notes that college bulletins remain definitive if discrepancies occur and that requirement displays reflect the current state rather than full history.

## Canonical table: `major_course_applicability`

Fields:

- `major_applicability_id`
- `source_system`
- `receiving_institution_source_id`
- `receiving_unitid`
- `receiving_program_source_id`
- `receiving_program_name`
- `degree`
- `requirement_block`
- `requirement_type`
- `requirement_rule_text`
- `course_source_id`
- `course_code_or_label`
- `choice_logic`
- `credits`
- `minimum_grade`
- `source_url`
- `retrieved_at`
- `evidence_status`

UNITID remains null until the separate CUNY identity layer accepts the institution match.

## Evidence layers kept separate

### A. Course equivalency

`Sending course(s) → receiving course(s)`.

This says what credit/equivalent course the receiving institution currently assigns. It does not by itself say where that course applies in the student's target program.

### B. Course-level attributes

Examples: Major Gateway, Universal Transfer, Pathways category.

These are useful transfer signals and explanation features, but remain distinct from program-specific degree applicability.

### C. Program requirement applicability

`Receiving program → requirement block/rule → receiving course or course choice`.

This is the strongest available T-Rex evidence for whether a transferred equivalent can satisfy a displayed program requirement.

### D. Policy/constraint context

Residency rules, minimum grades, prerequisites, admission conditions, and bulletin authority remain conditions. They are not collapsed into a binary transferable/not-transferable field.

## Join path

The intended evidence chain is:

`sending course expression`
→ `CUNY equivalency`
→ `receiving course identity`
→ `major_course_applicability`
→ `receiving program`
→ `program/CIP crosswalk`
→ existing `CIP ↔ SOC` pathway.

Each join has its own coverage metric.

## Recommendation features

Permitted explainable features include:

- `has_receiving_course_equivalency`
- `has_program_requirement_evidence`
- `requirement_block_type`
- `major_gateway_flag`
- `universal_transfer_flag`
- `pathways_core_category`
- `minimum_grade_condition_present`
- `residency_condition_present`
- `compound_equivalency_flag`
- `applicability_evidence_date`

Do not create a universal opaque transfer score from these fields before validation/calibration.

## Missing-data rules

- No T-Rex equivalency ≠ course will not transfer.
- Equivalency without program applicability ≠ elective-only credit.
- Major Gateway label ≠ guaranteed satisfaction of every matching major.
- Missing historical requirement data ≠ current rule applied historically.
- Missing UNITID/CIP mapping does not delete source evidence.

## Compound rules

Preserve explicit `AND` and `OR` relationships. Never split `A AND B → C` into two claims that A alone or B alone transfers as C. Do not infer Boolean structure merely from commas or punctuation.

## QA gates

1. Stable applicability IDs are unique.
2. Every applicability row has receiving-program identity.
3. Program/source URL and retrieval date are retained.
4. AND/OR source logic is preserved where explicitly present.
5. Course equivalency and major applicability are not conflated.
6. Missing UNITID/CIP remains visible rather than dropping rows.
7. Requirement-count changes across snapshots are reported by program/block.
8. Program requirements with no current course mapping remain explicit coverage gaps.

## Coverage baseline to establish

For the first authoritative run report:

- programs observed by receiving institution;
- requirement blocks per program;
- applicability rows;
- rows with stable program source IDs;
- rows with stable course source IDs;
- accepted UNITID rate;
- program→CIP mapping rate;
- explicit AND/OR rule counts;
- minimum-grade-condition coverage;
- programs/blocks with unresolved course mappings.

Do not invent regression floors before this run.

## Current implementation

`cuny_major_applicability_adapter.py` normalizes a saved authoritative T-Rex program-requirements snapshot/export into the canonical table. It preserves raw rule text and only assigns AND/OR when explicitly present in source text or supplied source fields.

## Next step

Capture representative authoritative Program Requirements records across receiving institutions, establish the first coverage/schema baseline, then implement the program identity/CIP bridge so this layer can connect transfer applicability to the existing college → program → occupation model without turning taxonomy proximity into transfer-policy evidence.
