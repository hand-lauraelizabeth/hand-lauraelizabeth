# S3-10 — Filter inventory using existing national data

**Audit:** 2026-10-11T01:19:02.305909+00:00

The 6,243-source-row national projection has **23 indexed fields** across 13 SHA-verified shards; the compact browser v2 JSON includes only a subset. All counts below were computed from those shards, not guessed from documentation.

| Filter | Availability | Nonmissing records | Interpretation |
|---|---|---:|---|
| School name search | browser | 6243 | Text search; distinguish name from type. |
| State / territory | browser | 6243 | Use stated source state; 59 valid codes in national file. |
| City label | browser | 6243 | Free text/autocomplete; city string is not a campus polygon or ZIP. |
| Control: public/private nonprofit/private for-profit | browser | 6243 | Codes 1, 2, 3 mapped; one control per action. |
| Campus setting: city/suburb/town/rural | browser | 5712 | 531 unknown; exclude on chosen value, report unknown. |
| Undergraduate size bands | browser | 5462 | Under 5k / 5k–14,999 / 15k+; null excluded. |
| Predominant degree level | source only | 6243 | Original coded field; validate user wording and unknown values. |
| Highest degree level | source only | 6243 | Original coded field; not evidence all specific programs offered. |
| Tuition: in-state / out-of-state | source only | 3601 | 3,601 with tuition; residency/pricing cohorts vary. |
| Total annual cost | source only | 5022 | Cost cohorts differ; no personalized tuition claim. |
| Average net price after grant aid | source only | 5021 | 5,021 source values; not family's specific award. |
| Average net price by income bracket | source only | 5021 | Income brackets only; NO family-size field. |
| Admissions selectivity | source only | 1909 | 1,909 observations; low coverage and not individual chance. |
| SAT / ACT average | source only | 1037 | SAT 1,037; ACT 970; descriptive only. |
| Academic subject mix (CIP2) | source only | 5468 | Broad discipline shares, not verified specific majors. |
| School ZIP | requires new source | 0 | Not in 23-field projection or v2 JSON; official separate dated source needed. |
| Campus housing / roommates | requires new source | 0 | Not in 23-field projection. |
| Family size, aid type, individualized need | requires new source | 0 | Income net-price brackets are not family size or grants inventory. |
| Distance, commute, campus accessibility | requires new source | 0 | Require campus point/accessibility evidence and disclosed metric. |

## Suggested user-facing order

1. Geographic: state/territory then **city** search (not ZIP; source has no ZIP).
2. Control: public, private nonprofit, private for-profit.
3. Setting and size: city/suburb/town/rural and undergraduate enrollment bands.
4. Additional data already compiled in original source shards: predominant/highest degree, in/out-state tuition, annual cost, income-bracket net price, admissions rate, average SAT/ACT and broad academic fields, after new v2 projection and QA.

## Current behavior constraints

- Keep one active filter at a time until the current working UI explicitly supports combinations.
- Selecting a known value excludes null or unsupported source codes; visible results counts and unknown totals must match.
- Avoid presenting national acceptance rates as probability of individual admission, or average net prices as household-specific awards.
- No school ZIP, housing availability, specific major offering, legal branch relationship or road distance is derived from city labels.
- No new UI, data asset, or WordPress change was made during this task.
