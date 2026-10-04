# Institution → Local Labor Market Coverage Contract

**Status:** executable join implemented; authoritative end-to-end data run pending upstream normalized snapshots.

## Purpose

This layer connects an institution to current local occupational evidence without treating geography as a name-matching problem and without converting missing/suppressed data into negative labor-market evidence.

Canonical chain:

`UNITID → county GEOID → May 2025 OEWS area → SOC occupation → local employment/wage evidence`

This layer is descriptive evidence. It is not, by itself, a recommendation score.

## Inputs

1. `institution_county.csv`
   - `UNITID`
   - `county_geoid`
   - optional institution/county lineage fields
2. `county_oews_area.csv`
   - `county_geoid`
   - `oews_area_code`
   - optional `area_title`, `area_type`, source/vintage fields
3. `oews_local_occupation.csv`
   - `oews_area_code`
   - `occ_code`
   - available May 2025 OEWS measures and lineage

The inputs should be produced by the existing IPEDS/Census county bridge, county→OEWS-area bridge, and May 2025 OEWS local adapter. No city-name or ZIP fallback is performed here.

## Outputs

- `institution_local_labor_market.csv`: one institution-level geography record per UNITID.
- `institution_local_occupation_evidence.csv`: institution × local occupation evidence.
- `institution_local_labor_market_coverage.csv`: institution counts by geography coverage state.
- `institution_local_labor_market_qa.csv`: compact regression/coverage metrics.

## Coverage states

Institution geography is explicitly classified as:

- `resolved`
- `missing_county`
- `county_not_mapped_to_oews_area`

Occupation evidence is separately classified. A resolved local market does not imply that every SOC has a published estimate in that area.

For selected OEWS measures, the adapter distinguishes:

- published local measure
- occupation not published for area
- occupation record present but selected measures suppressed/missing

Suppression is never converted to zero.

## QA invariants

1. `UNITID` must be unique in the institution-county input.
2. `county_geoid` must be unique in the county→OEWS-area input used for the institution join.
3. An institution with missing county evidence must not be assigned an OEWS area through a text-name fallback.
4. An institution whose county is unresolved must remain unresolved.
5. Cross-state metropolitan areas remain one OEWS labor market when the upstream BLS definition assigns the same area code.
6. Nonmetropolitan areas are valid local labor markets.
7. A missing occupation-area record is not zero employment.
8. A suppressed wage/employment measure is not zero.
9. State/national estimates must not silently replace missing local estimates in this layer.
10. Source vintage must remain available upstream/downstream so May 2025 OEWS geography is not mixed invisibly with incompatible geography vintages.

## Initial regression metrics

The first authoritative run should record at minimum:

- institutions total
- institutions with resolved local area
- institutions unresolved by reason
- institution local-area coverage rate
- distinct OEWS areas reached
- institution × occupation rows
- distinct local occupations represented
- rows with at least one published selected local measure
- rows with all selected measures suppressed/missing
- occupation records absent by area

Do not set hard percentage floors until the first complete authoritative snapshot is run and reviewed. After that run, version the baseline and trigger review on material unexplained movement rather than treating normal annual BLS/IPEDS changes as automatic failures.

## Recommendation use

Local labor-market evidence should remain a separate explainable signal. A future matching model may show, for example, local employment level, wage distribution, concentration/location quotient, and evidence coverage alongside national projections. It should not infer that a program is poor because a local estimate is suppressed or unavailable, nor assume a student's intended post-graduation labor market is necessarily the institution's local market.

A later user-preference/geographic-fit layer can distinguish institution-local market, home market, intended destination market, remote/national market, and user-selected comparison markets.
