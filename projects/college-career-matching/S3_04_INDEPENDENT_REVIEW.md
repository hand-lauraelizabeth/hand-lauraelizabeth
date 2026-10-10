# S3-04 — Independent institutional/geographic evidence review

**Audit:** 2026-10-10T17:43:18.141422+00:00

Reprocessed all **32 bounded single-Census-place name candidates** and **20 pre-existing same-state ambiguous college/place matches** (52 total). The tested geographic place alternatives and census Gazetteer hashes are pinned to prior source-audited files. The review uses the official NCES/IPEDS institution directory by exact UNITID where available and the Census Geocoder geographic lookup for official directory coordinates, NOT a website search snippet. The complete case ledger is retained as a GitHub Actions artifact, not as a public map or a campus geocode lookup.

## Official-source availability

NCES directory: https://nces.ed.gov/ipeds/datacenter/data/HD2024.zip (year: 2024; records: 6072).

Census geocoder API: https://geocoding.geo.census.gov/geocoder/geographies/coordinates?x=...&y=...&benchmark=Public_AR_Current&vintage=Current_Current&format=json

Census's current geographic lookup and the Gazetteer's 2026 point files are **different products and may not have identical reference vintages**. IPEDS coordinates may approximate reported institution locations. Neither can alone certify a physical building or an accessible/driveable route.

| Result of 52-row evidence review | Records |
|---|---:|
| census polygon does not support candidates | 3 |
| census polygon not returned | 10 |
| census polygon supported candidate | 31 |
| no current ipeds identity | 8 |

**Official IPEDS records found:** 44/52; **complete street/ZIP and matching state:** 44/52; **IPEDS coordinates present:** 44/52; **Census lookup succeeded:** 44/52.

**No new mapping was accepted automatically.** Even official point-in-place evidence is a geographic *candidate* rather than proof of exact campus location. All 52 records remain unresolved for release until separately reviewed institutional address, main-vs-branch identity and vintage consistency are checked. Baseline 5,659 city label matches unchanged.

## Evidence and constraints

- NCES IPEDS directory ZIP provenance, schema and SHA are in the aggregate JSON.
- Source geographies come from the official US Census 2026 Gazetteer and the separately dated Census geocoder Current_Current endpoint.
- The 52-case GitHub Actions artifact (access governed by repository permissions) records UNITID, reported Scorecard city, IPEDS official institution/address, Census official names/GEOIDs and polygon-lookup statuses, **but no latitude/longitude values**.
- Never choose a city/CDP/town GEOID by name or proximity; point-in-polygon can only corroborate a location, not manufacture a campus address.
- Independent human verification of campus vs branch and dates is still required before a new city-level association is treated as approved.
- There is no Census-derived browser dataset, gzip budget claim, ZIP-origin feature, or WordPress change in this audit.

## Next requirement

Review evidence-ledger cases with publisher institutional contact pages or more current official campus-address source before approving a mapping. Keep the 584 unresolved baseline untouched pending that review. Sprint 2 staging remains private and subject to its separate device/host checks.

Publisher references: [NCES IPEDS data files](https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?year=-1), [Census Geocoder API](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html), [2026 Census Gazetteer](https://www.census.gov/geographies/reference-files/2026/geo/gazetter-file.html).
