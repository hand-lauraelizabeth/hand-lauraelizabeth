# College Scorecard affordability field mapping

## Source and population
Primary technical reference: U.S. Department of Education, College Scorecard Institution-Level Technical Documentation (September 2025):
https://collegescorecard.ed.gov/files/InstitutionDataDocumentation.pdf

The official College Scorecard data-download page reports a June 10, 2026 update and includes institution-level files through 2025–26. Choose and record the specific downloaded release and verify its actual CSV headers before using this importer; the publication year is not necessarily the reference year of each net-price variable. Official download page: https://collegescorecard.ed.gov/data/ . Documentation and dictionary: https://collegescorecard.ed.gov/data/data-documentation/ .

The five net-price income brackets are for **full-time, first-time undergraduate Title IV aid recipients**. For public institutions, net price is restricted to **in-state tuition-paying** students. Net price is cost of attendance less federal, state, and institutional grants/scholarships, not an individual aid offer. Income groups are nominal dollars, not inflation-adjusted. Program-year and other-calendar measures may refer to the largest program rather than the entire institution. Do not label these figures as prices for all students.

## Normalized UI cost keys
| UI key | Reported family income | Public CSV | Private CSV | Program-year CSV | Other-calendar CSV |
| --- | --- | --- | --- | --- | --- |
| 0_30k | $0–$30,000 | NPT41_PUB | NPT41_PRIV | NPT41_PROG | NPT41_OTHER |
| 30_48k | $30,001–$48,000 | NPT42_PUB | NPT42_PRIV | NPT42_PROG | NPT42_OTHER |
| 48_75k | $48,001–$75,000 | NPT43_PUB | NPT43_PRIV | NPT43_PROG | NPT43_OTHER |
| 75_110k | $75,001–$110,000 | NPT44_PUB | NPT44_PRIV | NPT44_PROG | NPT44_OTHER |
| 110k_plus | $110,000+ (official label; verify boundary convention in current dictionary) | NPT45_PUB | NPT45_PRIV | NPT45_PROG | NPT45_OTHER |

Do not substitute overall NPT4_PUB or NPT4_PRIV for an unavailable income-specific cell. Use null. Do not select the first non-null category across different reporting populations without first verifying institution calendar and ownership. CSV and API field names differ; validate against the data dictionary for the exact release before import.

## Publication gate
1. Preserve UNITID, institution name, release year, **net_price_reference_year** (the year assigned to the selected affordability measures), field names, retrieval date and source URL in the ingestion manifest. The importer requires both years and rejects a net-price year later than the release year. Verify the reference year from the exact release dictionary; do not infer it from the download date.
2. Resolve reporting population (public, private, program-year, other calendar) explicitly. For public records label the in-state restriction.
3. Retain suppressed, privacy-masked, missing or nonnumeric prices as null. Never replace with zero, average, or a different income band.
4. Confirm each price comes from the same institutional reporting year and matching population.
5. Treat accessibility and career-alignment ordinals as unavailable (null) unless a separate documented and auditable method supports them. They are not native College Scorecard net-price fields.
6. Do not publish a public-data.json bundle until all records pass structural validation, field provenance review, and browser tests.

## Current UI limitations
When a maximum cost is entered, the UI requires known selected-band net price to satisfy that constraint; without a ceiling, unknown-price records remain visible and affordability is not ranked. The point-based ranking remains a prototype, not a validated institutional quality or fit measure. The synthetic demonstration is not a verified dataset.
