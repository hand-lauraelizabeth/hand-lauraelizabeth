# CUNY T-Rex Institution Identity & Coverage Baseline

**Observed:** 2026-10-04  
**Status:** public college universe observed; UNITID execution pending current IPEDS HD snapshot

## Public T-Rex institution universe

The public CUNY-to-CUNY by Subject selector currently exposes the same 20 college labels on sending and receiving sides:

1. Baruch College
2. Borough of Manhattan CC
3. Bronx CC
4. Brooklyn College
5. City College
6. College of Staten Island
7. Guttman CC
8. Hostos CC
9. Hunter College
10. John Jay College
11. Kingsborough CC
12. LaGuardia CC
13. Lehman College
14. Medgar Evers College
15. NYC College of Technology
16. Queens College
17. Queensborough CC
18. School of Labor & Urban Studies
19. School of Professional Studies
20. York College

This is a **public T-Rex selector baseline**, not a claim that CUNY has only 20 institutions or that every CUNY unit is represented in every T-Rex feature.

## Coverage distinctions

T-Rex itself exposes different coverage by feature. The matching tool must therefore avoid a single misleading `trex_covered` flag.

Track at least:

- `cuny_course_equivalency_coverage`
- `cuny_major_applicability_coverage`
- `cuny_program_requirement_coverage`
- `cuny_program_comparison_coverage`
- `cuny_noncuny_evaluation_coverage`
- `cuny_entry_requirement_coverage`

As observed 2026-10-04:

- CUNY-to-CUNY course/subject selectors expose the 20-college public universe above.
- Map Credits to CUNY Major Requirements states that only majors at colleges awarding bachelor's degrees are currently included.
- Understand CUNY Major Requirements likewise states that only bachelor's-degree-awarding colleges are currently searchable.
- Program Comparison is beta and currently covers selected majors rather than all programs.
- Non-CUNY absence is not negative evidence: T-Rex states that an unlisted/evaluated course may still be considered upon admission.

## Identity implementation

`cuny_institution_identity.py` maps the exact T-Rex labels to the IPEDS backbone through a small reviewed alias table and current New York IPEDS HD reference.

Rules:

1. exact normalized IPEDS name may be accepted when unique;
2. version-controlled reviewed alias may be accepted when it resolves to exactly one current NY IPEDS row;
3. multiple candidates are review-only;
4. absent candidates remain unresolved;
5. unresolved identity never deletes T-Rex evidence;
6. no fuzzy automatic campus merge.

Outputs:

- `cuny_institution_identity.csv`
- `cuny_institution_identity_review.csv`
- `cuny_institution_identity_coverage.csv`

## Initial QA baseline

Before current IPEDS execution, the only numeric baseline asserted is:

- public course-equivalency selector labels: **20**
- sending selector: same 20 labels
- receiving selector: same 20 labels

Do not invent a UNITID match-rate floor before execution. After running against the current IPEDS HD snapshot, review unresolved identities and freeze the first evidence-backed match baseline.

## Recommendation semantics

CUNY transfer evidence must remain decomposed. A student-facing explanation can distinguish:

- course has a known directional equivalency;
- course carries a Major Gateway / Universal Transfer / Core designation;
- transferred course applies to a selected major requirement;
- course is evaluated but does not apply to that selected major;
- non-CUNY course has no published evaluation yet;
- program coverage is not yet available in the relevant T-Rex feature.

The last two states are **unknown/coverage states**, not transfer rejection.

## Next implementation step

1. Run the 20-label universe through `cuny_institution_identity.py` against the current IPEDS HD reference.
2. Freeze the first CUNY identity coverage baseline after review.
3. Implement `cuny_major_applicability` as a separate table linking source learning experience/course → receiving CUNY program → requirement/application evidence.
4. Keep Common Core/College Option evidence separate because T-Rex's Map-to-Major feature explicitly focuses on major requirements.
5. Integrate CUNY and SUNY transfer evidence under the shared transfer/pathway model without forcing the two systems into identical source semantics.
