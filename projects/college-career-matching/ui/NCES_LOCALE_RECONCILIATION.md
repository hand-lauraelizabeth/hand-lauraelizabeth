# NCES/IPEDS locale reconciliation — private evidence workflow

**Status (2026-10-08): pending independent NCES data acquisition; no real institution data approved for publication.** This document is an implementation plan, not a claim that code in the repository has executed or that any locale is verified.

The private 20-institution College Scorecard review queue has official housing, accessibility-service and financial-aid **source reviews** recorded, but none of those reviews establishes comprehensive campus accessibility, a housing-accessibility rating, or a historical net-price cohort year. Every real institution remains `DO_NOT_PUBLISH`.

## Reconciliation contract

1. Obtain an official NCES/IPEDS `HDYYYY.zip` or `HDYYYY.csv` directory release from https://nces.ed.gov/ipeds/datacenter/; preserve the original download, acquisition date, exact release/vintage, URL and SHA-256.
2. Match on exact six-digit `UNITID` (never institution-name similarity). Validate uniqueness and compare the raw `LOCALE` code against the Scorecard candidate. Preserve the full 12-code family/subtype: City (11–13), Suburb (21–23), Town (31–33), Rural (41–43).
3. Report `MATCH`, `CONFLICT`, `NOT_FOUND`, and `UNKNOWN_OR_NOT_APPLICABLE` distinctly. Do not infer a locale from an address or a service location; branch campuses and relocated instruction sites require separate investigation.
4. Keep any reconciliation output private. A code match does **not** grant publication permission. Explicitly check the source vintage, independent reviewer, and cohort-year mapping before release review.

## Work completed and outstanding

A standalone, dependency-free Python reconciliation utility and 11 synthetic unit tests were locally executed (11/11 passed). The utility records file hashes and blocks queue rows not marked `DO_NOT_PUBLISH`; it does not alter its inputs or publish results. **The Python implementation has not been committed to GitHub** because repository code writes were rejected by connector safety checks; the working artifact is retained privately in the portfolio file Library.

The official NCES directory ZIP could not be retrieved in this environment; **0/20 locale records are independently NCES-verified**. The private queue's accessibility source statuses were reconciled to 20/20 `PARTIAL_SOURCE_VERIFIED` on 2026-10-08 after ten official-source rechecks. This verifies source-level support processes only, not physical campus/housing accessibility. Historical income-band net-price cohort years remain 0/20 verified.

## NEXT

Acquire the official NCES HD directory file, execute the private reconciliation utility, inspect conflicts and multi-campus exceptions, and independently verify College Scorecard `NPT41`–`NPT45` reporting cohorts using the official dictionary. Separately repair the matcher UI's nullable-aid rendering and fail-closed external-data publication gate, then run browser regression tests and CI. Do not add a real institution payload to the website until independently reviewed and explicitly approved.
