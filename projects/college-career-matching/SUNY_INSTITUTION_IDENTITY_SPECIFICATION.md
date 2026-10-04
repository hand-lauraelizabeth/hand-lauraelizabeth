# SUNY → IPEDS Institution Identity Contract

**Status:** implementation-ready; execution baseline pending authoritative SUNY snapshot  
**Project:** College + Career Matching Tool

## Purpose

Resolve campus labels emitted by SUNY STEP transfer-agreement, Transfer Path, and Core Course sources to the existing IPEDS institution backbone without silently merging campuses or treating a similar name as proof of identity.

The implementation is `suny_institution_identity.py`.

## Why this precedes integrated transfer scoring

Transfer evidence can remain valid even when an institution crosswalk is unresolved. The pipeline therefore preserves the SUNY source record first and enriches it with UNITID only when identity evidence is sufficient. An unresolved crosswalk must not delete an agreement, path, or course-equivalency record.

## Inputs

### SUNY campus universe

A deduplicated campus table derived from the authoritative STEP snapshots. Preserve:

- `campus_source_id` when SUNY exposes one;
- exact source label;
- source URL;
- retrieval/snapshot metadata in the upstream source manifest.

The identity resolver also accepts labels carried in agreement fields (`partner_campus`, `four_year_partner`) so the first snapshot can be processed before a richer campus endpoint is available.

### IPEDS reference

Use the current IPEDS HD/institution directory already supporting the institution model. Required fields:

- `UNITID`
- `INSTNM`
- `STABBR`
- `CITY`
- `WEBADDR`

Only New York candidates are considered in this SUNY-specific resolver.

## Matching hierarchy

### 1. Exact normalized institution name — automatic

Case, punctuation, diacritics, whitespace, and `&`/`and` differences may be normalized. Exactly one New York IPEDS institution must match.

### 2. Reviewed alias — automatic only after review

A small version-controlled alias table can bridge documented naming differences such as a SUNY brand label versus an IPEDS legal/reporting name. Each alias is explicit; fuzzy similarity does not create aliases automatically.

### 3. Token-signature candidate — review only

A unique candidate after removal of generic institution words may be useful for review, but it is **not** auto-accepted. Generic words can collapse genuinely distinct campuses.

### 4. Multiple or absent candidates — unresolved/review

No automatic merge. Preserve the source record and place the identity in the review queue.

## Corroborating evidence for review

When manual/review logic is expanded, use evidence such as:

- official SUNY campus directory identity;
- campus address/city;
- official domain;
- system membership;
- source-specific campus identifier;
- IPEDS institutional history where a campus has renamed or merged.

Do not accept a match solely because names are similar.

## Outputs

### `suny_institution_identity.csv`

All source campuses with:

- source ID/label;
- UNITID when accepted;
- IPEDS name;
- match method;
- match status;
- candidate count;
- source URL;
- review note.

### `suny_institution_identity_review.csv`

Only `review` and `unresolved` records. This is intentionally first-class output, not an error file to be discarded.

### `suny_institution_identity_coverage.csv`

Baseline metrics:

- source rows;
- accepted matches;
- review candidates;
- unresolved;
- accepted-match rate;
- review-or-unresolved rate.

## Structural QA

The resolver fails when:

- a source row has no campus label;
- an accepted match lacks UNITID;
- an accepted match has more than one candidate.

## Coverage/regression QA

Do **not** invent a minimum accepted-match rate before the first authoritative snapshot runs. After the initial run:

1. inspect every unresolved/review case;
2. add only evidence-backed aliases;
3. record the post-review baseline;
4. establish a regression floor based on that observed baseline;
5. fail later builds on unexplained material deterioration.

Track agreement-side and path/core-course-side coverage separately because their campus universes may differ.

## Join behavior

Transfer tables retain both:

- the exact SUNY institution label/source identifier; and
- the accepted `UNITID` when available.

Downstream rules:

- missing UNITID does not delete transfer evidence;
- institution-level Scorecard/IPEDS enrichment requires accepted UNITID;
- program/CIP matching is measured independently of institution matching;
- no many-to-many relationship is collapsed to force a complete join.

## Explanation behavior

If transfer evidence exists but identity resolution is incomplete, the user-facing system may still cite the exact SUNY institutions/path evidence, but it must not attach unrelated IPEDS/Scorecard attributes until the institution identity is accepted.

## Next execution step

1. Capture the authoritative SUNY agreement/path/core-course snapshots.
2. Build the deduplicated campus universe.
3. Run `suny_institution_identity.py` against the current IPEDS HD reference.
4. Review unresolved/token candidates with official campus evidence.
5. Freeze the first evidence-backed identity coverage baseline.
6. Join accepted UNITIDs back to `transfer_agreement` and `transfer_path_course` without dropping unmatched records.
