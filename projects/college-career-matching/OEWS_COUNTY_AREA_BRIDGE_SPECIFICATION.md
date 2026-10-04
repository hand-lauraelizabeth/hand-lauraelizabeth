# May 2025 OEWS County → Labor-Market Area Bridge

Status: adapter implemented; authoritative full-universe execution pending capture of the BLS May 2025 definition workbook/table.

## Purpose

Connect an institution's county or county equivalent to the exact metropolitan or nonmetropolitan geography used by May 2025 OEWS. This bridge supports local occupational employment/wage evidence without guessing from city names or assigning a cross-state metro to only one state.

## Authoritative evidence

BLS publishes (1) May 2025 metropolitan/nonmetropolitan area definitions, including a downloadable XLSX, and (2) county/county-equivalent pages that point each county to its OEWS area. Cross-state metropolitan areas are intentionally listed under every constituent state.

Primary sources:
- https://www.bls.gov/OES/current/msa_def.htm
- https://www.bls.gov/OES/current/county_links.htm
- https://www.bls.gov/oes/2025/may/oessrcma.htm

## Canonical bridge

`oews_county_area_bridge.csv`

Fields:
- `county_area_bridge_id`: deterministic SHA-derived row key
- `state_abbr`
- `county_name`: authoritative county/county-equivalent label
- `area_code`: OEWS area code
- `area_name`
- `area_type`: metropolitan | nonmetropolitan
- `cross_state_area_flag`
- `oews_vintage`: `2025-05`
- `geography_match_method`: `authoritative_bls_county_area_definition`
- `source_url`
- optional `retrieved_at`

## Matching contract

Preferred production join:

`institution -> county FIPS/county equivalent -> BLS county-area bridge -> OEWS area code -> occupation-level OEWS estimates`

The present adapter preserves authoritative county labels because the BLS definition source is the evidence layer. A later county-identity adapter should attach Census county GEOID/FIPS before institution matching. Name-only matching must not be the production institution join.

## Semantic safeguards

1. A cross-state metro is one labor market. Do not split it into state-specific pseudo-markets.
2. Nonmetropolitan areas are valid OEWS labor markets, not missing metros.
3. Suppressed occupation estimates remain missing after the geography join.
4. State estimates remain a separate comparison layer; do not substitute them silently for missing metro/nonmetro estimates.
5. Every row is vintage-specific. Future OEWS boundary changes require a new bridge rather than overwriting 2025 geography.
6. County equivalents (including independent cities and current Connecticut planning regions where present in the BLS source) must be preserved as authoritative geographic units.

## QA gates

Fail ingestion when:
- source has zero rows;
- county/state or area code is blank;
- one state+county key maps to multiple distinct OEWS area codes within the same vintage.

Report:
- total rows;
- state/equivalent count;
- distinct OEWS areas;
- metro/nonmetro rows;
- duplicate county rows;
- ambiguous county-to-area assignments.

Duplicate source rows that resolve to the same area are surfaced for review but can be deduplicated in canonical output.

## Coverage reporting

After the full BLS definition universe is captured, create an empirical baseline for:
- counties/county equivalents represented;
- counties successfully mapped to an OEWS area;
- metro vs nonmetro distribution;
- distinct area codes;
- cross-state areas;
- institution counties resolved to the bridge;
- institutions lacking county identity;
- occupation rows available vs suppressed within each institution's labor market.

No coverage percentage should be asserted before that run.

## Next implementation step

Add the county identity layer using authoritative Census/IPEDS geographic identifiers so institution UNITID → county GEOID/FIPS → OEWS area is deterministic. Then join the bridge to the May 2025 local OEWS occupation table and produce institution-local labor-market coverage QA.
