# IPEDS Institution → County GEOID Identity Contract

**Status:** executable bridge implemented; full current-universe execution pending source snapshot capture.

## Purpose

Provide a deterministic institution geography key for the local labor-market layer:

`UNITID → county GEOID → May 2025 OEWS area → occupation employment/wages`

The bridge is intentionally code-based. Institution city, ZIP, county-name similarity, and coordinates are not silently substituted for an authoritative county code.

## Authoritative inputs

1. **IPEDS Directory (HD)** — institution identity plus `COUNTYCD` and `COUNTYNM`. The current production input should be versioned explicitly (initial compatible target: HD2024).
2. **U.S. Census Bureau county/county-equivalent reference** — current five-digit county GEOID built from two-digit state FIPS + three-digit county FIPS, or supplied directly as GEOID.
3. **BLS May 2025 OEWS area definitions** — downstream county → metro/nonmetro mapping; maintained as a separate bridge because OEWS geography has its own vintage and definitions.

## Identity rules

- Preserve `UNITID` as the institution key.
- Treat IPEDS `COUNTYCD` as a five-character code, retaining leading zeroes.
- Validate that code against the selected Census county-reference vintage.
- Do **not** repair an invalid/missing code by fuzzy matching `COUNTYNM`.
- County names are QA labels only. A name mismatch produces a review flag rather than a different code.
- Preserve IPEDS and Census vintages in every output row.
- A county code absent from the selected Census vintage remains unresolved for that vintage.

## Why vintages are explicit

County-equivalent geography changes. A valid institution location in one source vintage can fail a naïve join to another vintage. The model therefore records source vintages and routes discrepancies to review instead of silently translating geography.

This is particularly important for Connecticut planning-region county equivalents and any future Census county/county-equivalent changes.

## Outputs

### `institution_county_identity.csv`

- `unitid`
- institution name / state
- `county_geoid`
- IPEDS county label
- Census county label
- `county_identity_status`
- `county_name_review_flag`
- `match_method`
- `ipeds_vintage`
- `census_county_vintage`

### `institution_county_identity_qa.csv`

Counts institutions, resolved identities, missing IPEDS county codes, codes absent from the selected Census vintage, and county-name review flags.

## QA gates

Hard failure:
- blank UNITID;
- duplicate UNITID in the supplied institution universe.

Review / coverage state rather than fabricated match:
- blank/invalid `COUNTYCD`;
- county code not present in reference vintage;
- IPEDS/Census county-name disagreement.

## Downstream OEWS join

The next integration step joins `county_geoid` to the separately normalized May 2025 BLS county→OEWS-area bridge, then joins the resulting OEWS area code to occupation-level May 2025 OEWS records. This keeps institution identity, Census geography, BLS labor-market geography, and occupational estimates independently versioned and auditable.

## Recommendation semantics

Local labor-market evidence is contextual evidence, not a claim that a graduate must work in the institution's county/metro. Later matching should support at least:

- institution-local market;
- student's preferred work market(s);
- student's home/current market where relevant;
- national comparison.

Those views should remain separate rather than being averaged into a single unexplained geography score.
