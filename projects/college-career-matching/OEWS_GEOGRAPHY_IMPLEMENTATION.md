# OEWS Local Labor-Market Geography Layer

Status: adapter implemented; authoritative May 2025 state and metropolitan/nonmetropolitan snapshot execution pending.

## Purpose

Extend the existing national OEWS occupation layer to current geographic labor-market evidence without turning geography into a proxy for student preference or institutional quality.

## Authoritative source

BLS Occupational Employment and Wage Statistics (OEWS), May 2025. BLS publishes national, state, and metropolitan/nonmetropolitan estimates and downloadable files. The May 2025 estimates use OMB Bulletin 23-01 metropolitan definitions. OEWS-specific nonmetropolitan areas cover counties outside OMB metropolitan areas.

## Canonical grain

The normalized table is occupation × OEWS geography. Geography keys preserve the BLS AREA code and source level. Occupation keys preserve SOC/OEWS OCC_CODE.

Do not infer an OEWS area from an institution name or city string. A separate county/area bridge should use the authoritative BLS area-definition file.

## Evidence kept separate

- current estimated occupational employment
- mean/median and percentile wages
- employment precision / wage precision where published
- jobs per 1,000 and location quotient where published
- state versus metro/nonmetro geography
- data vintage

These are current labor-market context signals, not forecasts. BLS Employment Projections remain the forward-looking layer.

## Missing/suppressed data

Suppressed, unavailable, or nonpublishable OEWS cells remain missing. They must not become zero employment or zero wages. Missingness should be surfaced in recommendation explanations and coverage QA.

## Geographic matching rules

1. Preserve BLS AREA codes as authoritative geography identifiers.
2. Build county → OEWS area from the official May 2025 area-definition file, not text matching.
3. Cross-state metropolitan areas remain one labor-market area even when they appear under multiple state listings.
4. State estimates and metro/nonmetro estimates are parallel evidence, not additive observations.
5. Institution location can identify a local labor market, but student location preference is a separate user-input signal.

## Outputs

`oews_2025_geography_occupation.csv` — normalized occupation/geography evidence.

`oews_2025_geography_coverage.csv` — row, geography, occupation, duplicate, and missing-key QA.

## Recommendation use

Candidate explainable features include local median wage, local employment, local concentration/location quotient, state median wage, national comparison, and geographic data coverage. These should remain separate features until calibration and bias/sensitivity testing.

Do not interpret higher local wages as universally better without cost-of-living context. Do not interpret larger employment counts as individual job-opening probability. Do not combine OEWS employment levels with BLS projection growth into an opaque rank.

## Next implementation step

Build the authoritative May 2025 county → OEWS area bridge from BLS area definitions, then join the geographic OEWS layer to the existing SOC/O*NET/BLS pathway. Add regression floors and missingness reports before exposing geography to recommendation calibration.
