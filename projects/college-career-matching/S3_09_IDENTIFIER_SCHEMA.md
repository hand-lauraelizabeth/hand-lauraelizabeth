# S3-09 — Proposed nonbreaking identity schema (not deployed)

| Property | Interpretation |
|---|---|
| record_key | Required source-scoped opaque string, exactly as present in national 2026 Scorecard projection (6 or 8 digits); preserve 6,243 keys. |
| scorecard_source_unitid | Source-reported UNITID field in the original Scorecard projection. Retain eight-digit strings without declaring them NCES six-digit reporting IDs. |
| nces_ipeds_unitid | Nullable, six-digit official reporting-unit identifier; populate with exact corroborating NCES records/crosswalk, never truncation. |
| opeid6 | Nullable six-digit federal aid identifier directly copied from raw federal Scorecard OPEID6 once accessible. |
| opeid8 | Nullable eight-digit federal aid identifier directly copied from raw Scorecard OPEID. Do not copy the eight-digit UNITID key into it. |
| source_id_class | six_digit_scorecard_source or eight_digit_scorecard_source; no automatic legal campus/branch label. |
| parent_record_key | Null unless affirmative official dated crosswalk proves a reporting relationship, not same six-digit prefix alone. |
| verified_campus_point | Null absent campus-specific verified physical address and point, not Scorecard reporting city or Census internal point. |
| provenance | Source URL, archive SHA, shard SHA, source field, survey vintage, any NCES/OPEID crosswalk version, evidence review status. |

## Deployment gate

1. Keep existing 6,243 exact source keys and current one-active-filter/locale/size behavior unchanged. Introduce the schema as a research adapter/optional sidecar before user-facing copy.
2. Do not label all 6,243 keys certified IPEDS UNITIDs; show College Scorecard source record identifier as the neutral term.
3. Reattempt official June 2026 bulk ZIP or dated federal UNITID/OPEID crosswalk through authorized source; leave OPEID6/OPEID8 and legal parent unknown until verified.
4. Regression test exact 5,787/456 partition, IDs as strings, source hash/unique keys, no merging of branch locations, null on missing info and unchanged sort/filter results.
5. Any proposed new browser payload needs an independent deterministic 750 KiB gzip comparison; original file used 177,188 bytes, not evidence that a new asset passes.
6. Separate owner approval and authenticated WordPress Draft + mobile/accessibility/host-LCP QA for public wording or feature launch.
