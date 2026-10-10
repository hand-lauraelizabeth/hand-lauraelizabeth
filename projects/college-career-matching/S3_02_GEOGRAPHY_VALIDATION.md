# S3-02 — 2026 Census ZIP-area and place validation

**Source-data audit time:** 2026-10-10T17:31:55.291739+00:00

**Scope:** aggregate research evidence only, no campus point or public widget. The Source ZIP archives were processed in CI; no source ZIP or geography coordinate table was checked into the public repository.

## Verified source files

| Census archive | Records | Distinct GEOIDs | Valid internal points | Archive SHA-256 |
|---|---:|---:|---:|---|
| zctas | 33791 | 33791 | 33791 | f1e9046b91f6e60686a99343cb2752834c02b0764939403b331c78c017e2c54c |
| places | 32363 | 32363 | 32363 | af678e2d990827c89ee39b98c82de6e90b693c7361ff0e559ae3076670dd2863 |

See research_aggregate/s3_02_aggregate_coverage.json for original publisher URLs, ZIP and extracted TXT SHA-256, byte sizes, published HTTP date, member names, delimiter, schema, supported states and leading-zero GEOIDs. Required fields, unique 5-digit ZCTA and 7-digit Place GEOIDs, and legal latitude/longitude bounds validated.

## College Search city-level coverage (not campus coordinates)

5659 of 6,243 schools (90.65%) resolve to **one** Census Place by conservative normalized city/state label matching.

| Match outcome | Schools |
|---|---:|
| ambiguous place name | 20 |
| no exact place name | 553 |
| outside places geography | 11 |
| unique city place match | 5659 |

All 6,243 school records remain untouched. No unmatched, ambiguous or out-of-coverage school was assigned coordinates. No school-city point is represented as a campus coordinate.

## Limits and follow-up

Census 2026 Gazetteer ZCTAs use 2020 block geography and **are not USPS postal ZIPs**. The Census point is an internal point, **not a mathematical centroid** or a reliable campus location. Census national Places and ZCTAs cover the 50 states, DC and PR; unsupported island territories remain unresolved. The current valid USPS ZIP denominator is NOT measured.

Before public distance filtering, review unmatched city aliases independently, verify source rights and any campus locations, test ZIPs against a suitable current USPS reference, and assess compressed asset size and accessibility. Sprint 2 release/physical device QA is independent and still pending. No WordPress changes or public feature claims here.
