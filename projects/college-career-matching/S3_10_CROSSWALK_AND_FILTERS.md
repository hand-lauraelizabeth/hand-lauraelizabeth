# S3-10 — Federal reporting-roster identity evidence and Scorecard OPEID source status

**UTC audit:** 2026-10-11T01:19:02.305909+00:00

S3-10 preserves all 6,243 national College Scorecard projected source records and does not modify any location or WordPress page. The original June 2026 source ZIP has a pinned recorded SHA, but its raw OPEID6/OPEID8 fields are not accessible to this runner and remain null.

## Direct Scorecard ZIP recovery

Official source: https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_06102026.zip. HTTP HEAD status: <HTTPError 403: 'Forbidden'>. A successful HEAD response is not proof of retrieved CSV data; **no 2026 OPEIDs were extracted**.

## Alternative first-party federal reporting evidence

NCES publishes public IPEDS Institutional Characteristics survey responses at https://nces.ed.gov/ipeds/reported-data/html/135081?surveyNumber=1&viewmode=print&year=2024. These include a published **Branch Campus List** showing eight-digit branch IDs and campus names beneath a parent six-digit survey header (e.g., Keiser University). This is authoritative evidence of that reported 2024 survey-roster relationship, not proof of current 2026 legal, financial-aid or physical campus identity.

- Source-hashed 2025 NCES HD2025 directory records: 5985.
- Distinct six-digit reporting roots across the 456 source keys: **180**.
- Retrieved official NCES 2024 reporting pages: **180 / 180**.
- Pages with extractable explicit branch lists: **175**.

| 2024 NCES branch-list verification outcome | Extended Scorecard IDs |
|---|---:|
| 2024 source page without roster | 5 |
| listed as branch in 2024 nces reported data | 441 |
| not in 2024 parent branch list | 10 |

No current OPEID6/OPEID8 mapping is accepted from a numerical prefix. The 2024 reporting roster is a different published source from the inaccessible June 2026 Scorecard OPEID fields. Every record remains unchanged.

## Filter audit

See [national filter field inventory](./S3_10_FILTER_INVENTORY.md), validated against all 13 SHA-pinned national Scorecard projection shards. **School ZIP is not included in this projection.** City, state, ownership and campus setting can be supported without external geography; site browser v2 already contains those fields plus undergraduate size.

This research does not implement filters, changes to WordPress, browser data or distances. Full 456-record source/branch listing is retained as a 30-day CI artifact.

Sources: [IPEDS reporting-unit groupings](https://nces.ed.gov/ipeds/use-the-data/institutional-groupings-in-ipeds), [NCES 2024 published Keiser survey](https://nces.ed.gov/ipeds/reported-data/html/135081?surveyNumber=1&viewmode=print&year=2024), [College Scorecard files](https://collegescorecard.ed.gov/data/).
