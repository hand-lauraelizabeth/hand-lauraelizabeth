# S3-03 — Geographic identity mismatch review (research only)

**Completed source pass:** 2026-10-10T17:37:40.217049+00:00

Compared the *same SHA-256-pinned* Census 2026 Gazetteer Places archive and the same verified 6,243-institution College Scorecard snapshot as S3-02. The 584 unresolved school records are reviewed as public-source city/state labels, **not** personal addresses or verified campuses. The full non-coordinate review queue is a CI artifact only (not committed as a publicly browsable review list).

## Baseline remains unchanged

| Outcome | Schools |
|---|---:|
| ambiguous place name | 20 |
| no exact place name | 553 |
| outside places geography | 11 |
| unique city place match | 5659 |

## Alternative official-place-name *review probes* for 553 no-exact matches

Only exact equality to another **published 2026 Census Place name** within the same state is considered, with narrowly bounded punctuation/diacritic folding, an explicit redundant state-code suffix, or a first-token directional/name abbreviation. These probes are **candidates for manual source review**, never accepted coordinates or confirmed alternative campus addresses.

| Probe result | Schools |
|---|---:|
| multiple official place candidates | 19 |
| no official place candidate | 502 |
| one official place candidate | 32 |

**Hypothetical ceiling only, not an implemented result:** if every single-candidate probe were independently confirmed later, no more than 5691 of 6,243 school-city labels could be linked on this limited check. Actual verified and deployed match count is still **5,659**.

## Ambiguity and outside-coverage boundaries

20 school records match more than one published same-state Census Place; 16 distinct city/state labels are affected. Multiple legal/statistical places sharing a name cannot be resolved from the college city/state string alone. No arbitrary preference for city, CDP, incorporated place or one GEOID is allowed.

11 school records reside in state/territory codes absent from the national Census Places archive. No nearby substitute or foreign/country-level centroid is assigned.

## Largest unresolved areas and likely review priorities

- **NY**: 116 no-exact school records; most frequent raw labels: Brooklyn (53), Bronx (10), Staten Island (8), Flushing (5), Long Island City (5), Far Rockaway (3), Forest Hills (3), Jamaica (3), Astoria (2), Purchase (2)
- **PR**: 46 no-exact school records; most frequent raw labels: Bayamon (19), Manati (7), Mayaguez (7), Hato Rey (5), Juana Diaz (2), Mercedita (1), Rio Grande (1), Rio Piedras (1), San German (1), San Sebastian (1)
- **NJ**: 45 no-exact school records; most frequent raw labels: Bloomfield (4), Cherry Hill (3), Edison (3), Ewing (3), Wayne (3), Denville (2), Howell (2), Mahwah (2), Nutley (2), Piscataway (2)
- **CA**: 36 no-exact school records; most frequent raw labels: North Hollywood (5), Ventura (4), Hollywood (2), La Jolla (2), Northridge (2), Reseda (2), Sherman Oaks (2), Van Nuys (2), Woodland Hills (2), Canoga Park (1)

Top raw labels are *investigation leads*, **not** proof that the school campus is inside a Census Place or that the Scorecard city field is wrong. Full triage is available in the aggregate JSON and CI review artifact.

## Required independent evidence before any acceptance

For each candidate obtain a current authoritative *institution campus address* or accepted campus location data linked explicitly by UNITID, plus an authoritative municipality/census identity crosswalk as needed. Check date, main-vs-branch-campus identity, state, legal place type and possibly multiple campuses. Retain null for unconfirmed or unsupported cases. Census internal points are city-area proxies only, not campus points or transportation distances.

## Release and data boundaries

No official place coordinates, raw Census ZIP files, resolved school geocodes, distance control or new browser asset were committed. Therefore there is **no Sprint 3 browser gzip-budget measurement** and **no verified current-USPS-ZIP coverage**. Sprint 2 remains a private draft under separate mobile/authenticated QA and explicit approval gates. No WordPress edits or publication.

Source: [Census Bureau 2026 Gazetteer](https://www.census.gov/geographies/reference-files/2026/geo/gazetter-file.html) and [2026 record layout](https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/gaz-record-layouts.2026.html).
