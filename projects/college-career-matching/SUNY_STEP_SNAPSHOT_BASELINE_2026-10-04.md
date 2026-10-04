# SUNY STEP Live Snapshot Baseline — 2026-10-04

**Source:** SUNY Transfer Equivalency Platform (STEP) public Transfer Agreements page  
**Source URL:** https://step.transfer.suny.edu/agreements/  
**Observed/captured:** 2026-10-04  
**Status:** live-source structural baseline; full raw HTML/CSV payload capture remains pending a reproducible download path

## Live schema observed

The current public table exposes four columns:

1. `4 Year Partner Campus`
2. `Partner Campus`
3. `Type Description`
4. `Major or Program`

This is the current live presentation and supersedes the older indexed/search representation that exposed `ID`, `Initial Campus`, `Partner Campus`, `Type`, `Program`, `Destination`, and `Source` as if those were the current page schema.

## First live row-count baseline

The current public page returned **171 agreement rows** in the captured page representation on 2026-10-04.

This number is now an **observed source baseline**, not a permanent expected count. Later runs should compare against it and investigate material changes rather than requiring equality forever.

## Agreement-type values observed

The live table includes at least:

- `General Articulation`
- `Major Specific`
- `Dual Admission`
- `Dual Enrollment`

These labels should be preserved verbatim in the source layer and normalized only in derived fields.

## Semantic observations

The `Major or Program` field is heterogeneous. It can contain:

- explicit source → destination program pairs;
- a single program/path label;
- prose describing a broad agreement;
- counts or summaries of multiple pathways;
- degree conditions;
- institution-wide agreement descriptions.

Therefore it must **not** be mechanically split into sending and receiving programs unless the source string itself contains an unambiguous directional expression and the parsing rule is retained for review.

The partner fields can also contain system-level or grouped identities, e.g. `All SUNY Community Colleges`. Such rows are valid agreement evidence but cannot be forced into one IPEDS UNITID.

## Identity implications

Build the campus universe from both partner columns, but classify labels before UNITID resolution:

- `institution` — candidate for IPEDS UNITID;
- `subunit_or_school` — retain parent/institution relationship where supported;
- `institution_group` — e.g. all SUNY community colleges; do not force a UNITID;
- `unresolved_label` — review required.

Examples in the current source show why this is necessary:

- `Binghamton University (Harpur College)` includes a school/subunit context;
- `University at Buffalo (School of Pharmacy and Pharmaceutical Sciences)` includes a school context;
- `SUNY Upstate Medical University (College of Nursing)` includes a college context;
- `All SUNY Community Colleges` is a group, not an institution.

## Regression rules established from this baseline

Until at least one subsequent snapshot exists, use warning-oriented gates rather than pretending natural source changes are errors:

- source page must expose all four expected live columns;
- source row count must be > 0;
- a change of more than 20% from the 171-row baseline triggers manual review;
- zero rows or missing required columns fail ingestion;
- novel `Type Description` values are preserved and flagged for taxonomy review rather than dropped;
- blank partner fields are counted and surfaced;
- duplicate exact rows are counted and surfaced, not silently removed from the raw snapshot;
- group/subunit labels remain visible through identity resolution.

After a second authoritative snapshot, replace the provisional 20% review threshold with a change policy informed by observed source behavior.

## Reproducibility limitation

The page was captured through a current web representation that exposed the full table and its 171 rows, but this run did not obtain a raw downloadable HTML/CSV artifact suitable for committing as the immutable raw snapshot. Do not claim raw-snapshot completion until the payload is saved and hashed.

## Next executable step

Use the 171-row structural baseline to harden the agreement adapter and campus-universe builder, including group/subunit classification. Then, when a raw payload is available, execute the adapter and `suny_institution_identity.py`, record accepted/review/unresolved counts, and freeze the first identity-coverage baseline.