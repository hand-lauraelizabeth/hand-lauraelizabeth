# S3-09 — National source identifier provenance (456 eight-digit keys)

**Audit:** 2026-10-11T01:12:13.665896+00:00 UTC. **Research only — WordPress/production dataset unchanged.**

## Verified facts

All **6,243** national records and 13 previously SHA-pinned projection shards validate identically. The source manifest declares the June 10, 2026 College Scorecard institution-level ZIP with archive SHA-256 f56a181b000ca4914e924c16b6b81dcc656e25aeb2ac68ab7d271ac0f29ffd58. **5,787 national record keys are six digits; 456 are eight digits.** Every eight-digit value occurs in those checked-in source-derived shards. The official **2025 NCES IPEDS directory** was also re-downloaded with pinned SHA-256 aadad9277a2255c85813b6d206475ddbf8a7330d79cc0236c2ecae685b00f1bf.

## Original Scorecard ZIP retrieval

**BLOCKED:** official source ZIP https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_06102026.zip returned HTTPError: HTTP Error 403: Forbidden. Therefore **this run has NOT independently verified the original CSV UNITID/OPEID fields**. Eight-digit IDs are SHA-validated in the national projected source shards, but genuine raw OPEID6 and OPEID8 values are **unknown/null**. The earlier manifest's source-archive SHA is retained as a recorded provenance claim, not falsely counted as a newly downloaded archive.

## Classification for all 456 source-projected extended keys

| Evidence class (not a legal parent/branch proof) | Records |
|---|---:|
| scorecard and nces prefix observed opeid relationship unverified | 456 |

Distinct six-digit numeric prefixes: 180. A prefix that exists as an official 2025 NCES UNITID may indicate a reporting-family relationship, but it is not a certified parent crosswalk. Never inherit its geolocation.

## Schema and data-release planning

See [identity migration contract](./S3_09_IDENTIFIER_SCHEMA.md). Stable source record keys must remain strings and all 456 eight-digit records must be preserved. Do not collapse Scorecard projected source UNITID, six-digit NCES survey identifier, eight-digit OPEID, or physical campus into a single field. Until the original 2026 ZIP or authoritative crosswalk can be fetched, both OPEID fields remain **null**, not inferred from the numeric prefix.

The full no-coordinate 456-row classification ledger is stored as a 30-day GitHub Actions artifact. Persistent aggregate evidence: [S3-09 JSON](./research_aggregate/s3_09_identity_provenance_summary.json).

Original unchanged Sprint 2 data payload gzip: 177188 bytes / 768000 budget, headroom 590812. No enriched browser asset created; research-ledger gzip estimate 13093 bytes is not a browser release measurement.

No new parent/NCES UNITID approvals, campus points, ZIP distance, browser filter, or WordPress edits.

Publisher references: [College Scorecard source](https://collegescorecard.ed.gov/data/), [Scorecard institutional technical documentation](https://collegescorecard.ed.gov/files/InstitutionDataDocumentation.pdf), [official NCES institution groupings](https://nces.ed.gov/ipeds/use-the-data/institutional-groupings-in-ipeds).
