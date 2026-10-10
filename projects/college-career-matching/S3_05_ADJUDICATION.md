# S3-05 — Adjudicated institution–Census-place identities

**Review date:** 2026-10-10T17:49:37.186400+00:00

**Research-only: no new coordinates, no distance control, no WordPress edits, no site release.**
The input is the immutable 52-case candidate review set derived from 32 bounded aliases and 20 Census ambiguities. Source records from 2026 Census and 2024 NCES IPEDS are independently checked; institution-controlled website pages are inspected for the explicitly reviewed cases. The output registry identifies a **Census Place GEOID only**, never an address, building, latitude/longitude, accessible route or campus coordinate.

## Decision counts

| Adjudication | Records |
|---|---:|
| approve census city place proxy | 3 |
| hold missing 2024 ipeds identity | 8 |
| hold multiple campuses transition | 1 |
| hold postmerger unitid | 1 |
| hold unverified institutional campus | 38 |
| reject suggested place not supported | 1 |

**Approved city-place proxies:** 3 / 52 researched cases. All others carry null/unassigned Census place identity for this proposal.
**Existing public baseline remains 5,659/6,243:** these review results are not deployed and cannot be added to user-facing coverage until a separate release gate.

## Source-verified individual cases

- **UNITID 107840 — Shorter College:** approve_census_city_place_proxy; [institution-controlled page](https://shortercollege.edu/contact-us-full/); proposed Census place: 0550450. Official North Little Rock campus contact address; Scorecard abbreviation only.
- **UNITID 150303 — Tricoci University of Beauty Culture — Highland campus:** approve_census_city_place_proxy; [institution-controlled page](https://www.tricociuniversity.edu/contact-us/); proposed Census place: 1833466. Institution distinguishes Highland campus; Census point-in-place selected only one same-name place.
- **UNITID 170639 — Lake Superior State University:** approve_census_city_place_proxy; [institution-controlled page](https://www.lssu.edu/campus-map/); proposed Census place: 2671740. Official campus map and address; typographic abbreviation of Sault Ste. Marie only.

## Institutional identity and multi-campus holds

- **UNITID 115746:** Pacifica currently lists Carpinteria Lambert and Santa Barbara Ladera locations, and a dated 2026–27 consolidation; do not force unqualified Scorecard city to one permanent Census place. [1](https://www.pacifica.edu/) / [2](https://www.pacifica.edu/pacificas-campus-transition/). Decision: hold_multiple_campuses_transition.
- **UNITID 125897:** Redlands reports completed July 6 2026 merger; continuing institution is Redlands with former Woodbury campus now Redlands Los Angeles. The original Woodbury UNITID needs post-merger verification even though Burbank campus address remains published. [1](https://www.redlands.edu/about/office-of-the-president/presidents-messages/2026/university-of-redlands-and-woodbury-university-complete-historic-merger) / [2](https://woodbury.edu/about/people/directory/). Decision: hold_postmerger_unitid.

## Acceptance rules and remaining work

- Approval requires a valid UNITID, consistent campus state/city, one Census place GEOID supported by IPEDS/Census point-in-place, and a contemporaneously fetched institution-controlled campus address. It does **not** validate campus coordinate precision.
- Approved records are tagged as **research-only city-place identities**. For any future feature, accurate campus points and current official campus identity must be reviewed independently; no driving/transit claims.
- Missing census place polygons, missing historical IPEDS institutions, potential parent/branch changes, or institution mergers remain null.
- Full case-by-case notes are in the restricted-to-repository-permissions GitHub Actions evidence artifact, not a public address/coordinate dump.
- The official IPEDS 2025 directory should be rechecked (the previous 2025 raw ZIP request failed); merger-aware identifier updates must occur before any national coverage promotion.

Sources: [2026 Gazetteer](https://www.census.gov/geographies/reference-files/2026/geo/gazetter-file.html); [IPEDS directory downloads](https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?gotoReportId=7); [Census Geocoder](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html).
