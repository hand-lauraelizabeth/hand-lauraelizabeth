# S3-07 — Official NCES HD2025 source recovery and 49-case comparison

**Audited (UTC):** 2026-10-11T00:19:30.386281+00:00

**Research only.** Source records and case decisions are not campus geocodes, ZIP coverage, driving distances, or authorization to change WordPress.

## Official NCES source and provenance

- [NCES Complete Data Files catalog](https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?gotoReportId=7)
- Official HD2025 ZIP URL: https://nces.ed.gov/ipeds/complete-data-files/HD2025.zip
- **Verified authentic NCES hosted ZIP**; 5985 unique official 2025 UNITIDs.
- ZIP SHA-256: `aadad9277a2255c85813b6d206475ddbf8a7330d79cc0236c2ecae685b00f1bf`
- extracted CSV SHA-256: `3f48135a1de007d68f110635a18fe23e93c2ad85f760c08755827657fccb076f`
- archive byte size: 1009677
- release caveat: 2025–26 provisional institutional directory; not an October 2026 campus registry.

2024 control archive: SHA-256 `d98425c123d7c0e872aec6e83960dfb501884818bf17385c340790f3d1f28345`, 6072 unique UNITIDs.
The earlier guessed /ipeds/datacenter/data/HD2025.zip and HD2025_P.zip endpoints returned HTTP 404; S3-07 tests the publisher's /ipeds/complete-data-files/ distribution instead.

## Source-year reconciliation for the 49 unresolved S3-05 cases

| Comparison result | Schools |
|---|---:|
| missing both | 8 |
| present both | 41 |

Differences in names: 0; differences in city: 1; differences in state: 0.
Neither missing entries nor name changes prove a closure or merger. All changes require publisher identity evidence.

## Pending dispositions

| Disposition | Records |
|---|---:|
| hold 2025 directory record campus unverified | 38 |
| hold missing 2025 directory identity | 8 |
| hold pacifica campus transition | 1 |
| hold woodbury merger continuing unitid | 1 |
| reject unsupported census place candidate | 1 |

Woodbury (UNITID 125897) remains on an explicit post-merger identity hold; Pacifica (115746) remains on a two-campus transition hold; the previous unsupported Census place candidate (491923) stays rejected.
All new location approvals: **0**. Existing 3 research-only Census place IDs are unchanged. Baseline 5,659/6,243 school-city matches and 584 outstanding location-release uncertainties are unchanged.

Complete 49-case comparison, including names, source-year city/state, and potential six-digit UNITID prefixes, is retained as a 30-day GitHub Actions artifact governed by repository access.

## Separate release gates

Current institutional/campus identity and addresses require current institution-controlled sources and verified parent/branch reporting; 2025 IPEDS alone is not campus geolocation. Future ZIP features must separately verify current USPS coverage, Census ZCTA precision, browser gzip budget, and physical-device/mobile QA.
No WordPress edits or deployable distance feature were made.

Publisher references: [NCES IPEDS](https://nces.ed.gov/ipeds), [Data Center complete files](https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?gotoReportId=7), [official archive](https://nces.ed.gov/ipeds/complete-data-files/HD2025.zip), [Woodbury/Redlands merger](https://www.redlands.edu/about/office-of-the-president/presidents-messages/2026/university-of-redlands-and-woodbury-university-complete-historic-merger), [Pacifica transition](https://www.pacifica.edu/pacificas-campus-transition/).
