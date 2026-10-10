# S3-06 — NCES 2025 retrieval and official institution change reconciliation

**Date:** 2026-10-10T18:02:22.626186+00:00

Reconciled all **49 S3-05 nonapproved cases** against the current directory when retrievable, the verified 2024 NCES directory, institution-declared website URLs, and two dated institution-controlled merger/transition sources. **No unverified mapping was accepted, no website data or coordinates were changed.**

## 2025 NCES IPEDS availability

NCES official catalog lists **HD2025** as 2025 Institutional Characteristics Directory (see [official catalog](https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?gotoReportId=7)). The raw ZIP request is not presumed successful merely because its metadata is listed.

- https://nces.ed.gov/ipeds/datacenter/data/HD2025.zip: **unavailable**: HTTP Error 404: Not Found
- https://nces.ed.gov/ipeds/datacenter/data/HD2025_P.zip: **unavailable**: HTTP Error 404: Not Found

**BLOCKER:** The official HD2025 data could not be retrieved and parsed through audited URLs in this run. **Never relabel 2024 as 2025.** Full 2025 identity reconciliation is therefore pending.

## 49-case identity decisions

| Source-bound status | Schools |
|---|---:|
| hold 2024 directory only | 38 |
| hold no official directory unitid | 8 |
| hold pacifica two campuses until 2027 consolidation | 1 |
| hold woodbury redlands identity change | 1 |
| reject previous census place candidate | 1 |

**Directory evidence:** 41/49 appear in NCES 2024; 41/49 have listed institution websites; 37/49 homepages returned a readable response. A reachable homepage is **not** a verified current campus address.

## Primary-source institutional changes

**Woodbury (former UNITID 125897):** The [July 6, 2026 University of Redlands announcement](https://www.redlands.edu/about/office-of-the-president/presidents-messages/2026/university-of-redlands-and-woodbury-university-complete-historic-merger) confirms Redlands is the continuing institution and that Woodbury operates as Redlands Los Angeles. Retain the old UNITID as a **historical/merger hold** until the federal institution/branch crosswalk gives the continuing UNITID. Do not silently assign the historic Woodbury record to a Redlands campus.

**Pacifica (UNITID 115746):** The [official July 2026 updated transition note](https://www.pacifica.edu/pacificas-campus-transition/) says Lambert-based students remain there through fall 2026 and residential sessions consolidate at **Ladera in winter 2027**; Lambert lease ends April 2027. Keep location time- and campus-specific. Do not present Ladera as the only October 2026 instructional location.

Source page retrieval metadata and required-term checks are recorded in the [machine-readable aggregate summary](./research_aggregate/s3_06_reconciliation_summary.json).

## Geographic and release constraints

- 8 formerly missing 2024 directory UNITIDs are individually tracked, including possible six-digit prefix parents where the official directory confirms one. A numeric prefix is **not** proof of legal parentage.
- Other 38 previously unverified institutional addresses and the single Census-contradicted place remain held or rejected, never automatically promoted.
- A **52-case release registry was not produced**; the three S3-05 research-only Census place identifiers remain unchanged and undeployed.
- No ZIP centroid, full USPS ZIP coverage, driving distance, campus point, new browser bundle size, new filter, WordPress publish, or Draft 1154 edit is claimed.

**Next review gate:** Resolve published HD2025 delivery path or official NCES data-generator/Access export, then current institutional location and OPEID/UNITID merger lineage with dated source-level evidence; do not accept outstanding GEOIDs until geographic and institutional identities are independently grounded.
