# College Scorecard affordability field mapping

## Source and population
Primary technical reference: U.S. Department of Education, College Scorecard Institution-Level Technical Documentation (September 2025):
https://collegescorecard.ed.gov/files/InstitutionDataDocumentation.pdf

The official College Scorecard data-download page reports a June 10, 2026 update and includes institution-level files through 2025–26. Choose and record the specific downloaded release and verify its actual CSV headers before using this importer; the publication year is not necessarily the reference year of each net-price variable. Official download page: https://collegescorecard.ed.gov/data/ . Documentation and dictionary: https://collegescorecard.ed.gov/data/data-documentation/ .

The five net-price income brackets are for **full-time, first-time undergraduate Title IV aid recipients**. For public institutions, net price is restricted to **in-state tuition-paying** students. Net price is cost of attendance less federal, state, and institutional grants/scholarships, not an individual aid offer. Income groups are nominal dollars, not inflation-adjusted. Program-year and other-calendar measures may refer to the largest program rather than the entire institution. Do not label these figures as prices for all students.


**Verified official 2026 download link:** https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_06102026.zip (linked from https://collegescorecard.ed.gov/data/). The download is a ZIP archive; extract its institution-level CSV before calling `import_scorecard.py`. The importer accepts this official source URL in metadata but does not download, unpack, authenticate, or verify the file checksum. The dictionary is https://collegescorecard.ed.gov/files/CollegeScorecardDataDictionary.xlsx; its cohort-map worksheet must be consulted to assign `net_price_reference_year` correctly. The official download URL alone does not establish the metric reference year.

## Normalized UI cost keys
| UI key | Reported family income | Public CSV | Private CSV | Program-year CSV | Other-calendar CSV |
| --- | --- | --- | --- | --- | --- |
| 0_30k | $0–$30,000 | NPT41_PUB | NPT41_PRIV | NPT41_PROG | NPT41_OTHER |
| 30_48k | $30,001–$48,000 | NPT42_PUB | NPT42_PRIV | NPT42_PROG | NPT42_OTHER |
| 48_75k | $48,001–$75,000 | NPT43_PUB | NPT43_PRIV | NPT43_PROG | NPT43_OTHER |
| 75_110k | $75,001–$110,000 | NPT44_PUB | NPT44_PRIV | NPT44_PROG | NPT44_OTHER |
| 110k_plus | $110,000+ (official label; verify boundary convention in current dictionary) | NPT45_PUB | NPT45_PRIV | NPT45_PROG | NPT45_OTHER |

Do not substitute overall NPT4_PUB or NPT4_PRIV for an unavailable income-specific cell. Use null. Do not select the first non-null category across different reporting populations without first verifying institution calendar and ownership. CSV and API field names differ; validate against the data dictionary for the exact release before import.

## Local CSV preflight
After downloading the official institution-level ZIP, run `python preflight_scorecard.py /path/to/institution.zip PUB` directly (when the ZIP contains exactly one CSV), or use an extracted file with `python preflight_scorecard.py /path/to/institution.csv PUB` (or `PRIV`, `PROG`, `OTHER` as appropriate) to check the required header family before creating reviewed metadata. The preflight also prints the SHA-256 digest of the exact input CSV or ZIP for the ingestion manifest; save it with retrieval date and source URL so later runs can identify changed input bytes. A digest alone is not independent proof of authenticity. This is a read-only schema check, not a verification of source authenticity, reference years, or individual institution records. The preflight uses only Python's standard library.

## Publication gate
1. Preserve UNITID, institution name, release year, **net_price_reference_year** (the year assigned to the selected affordability measures), field names, retrieval date and source URL in the ingestion manifest. The importer requires both years and rejects a net-price year later than the release year. Verify the reference year from the exact release dictionary; do not infer it from the download date.
2. Resolve reporting population (public, private, program-year, other calendar) explicitly. For public records label the in-state restriction.
3. Retain suppressed, privacy-masked, missing or nonnumeric prices as null. Never replace with zero, average, or a different income band.
4. Confirm each price comes from the same institutional reporting year and matching population.
5. Treat accessibility and career-alignment ordinals as unavailable (null) unless a separate documented and auditable method supports them. They are not native College Scorecard net-price fields.
6. Do not publish a public-data.json bundle until all records pass structural validation, field provenance review, and browser tests.

## Current UI limitations
When a maximum cost is entered, the UI requires known selected-band net price to satisfy that constraint; without a ceiling, unknown-price records remain visible and affordability is not ranked. The point-based ranking remains a prototype, not a validated institutional quality or fit measure. The synthetic demonstration is not a verified dataset.

## June 2026 source verification (October 7, 2026)
The original 23,559,465-byte archive was retrieved from the dedicated Google Drive intake folder. Its main CSV has 6,273 institution rows and 3,308 distinct columns, including `UNITID`, `INSTNM`, `CONTROL` and all `NPT41`–`NPT45` population variants. `CONTROL` counts: public (`1`) 2,047; private nonprofit (`2`) 1,901; private for-profit (`3`) 2,325. The ZIP also contains a `__MACOSX/` resource-fork sidecar; the preflight ignores it. The official College Scorecard glossary labels overall `NPT4_PUB` and `NPT4_PRIV` as **2023–24 award-year cohort** in the current release, but do not assume every field shares the same year: confirm `NPT41`–`NPT45` against the official dictionary cohort map before assigning `net_price_reference_year`. The glossary also notes that negative net prices can occur when grants exceed attendance cost; the importer currently rejects negative numbers, so resolve the display/validation semantics before importing any such records. No institutional data have been published.


## Signed net-price values
The importer, bundle validator, and browser now preserve finite negative average net prices rather than silently converting them to zero or rejecting the record. The UI formats a negative value as `−$275`, and affordability fit is clamped to the existing 0–1 scoring range. A negative *average* net price is not a promise of an individual refund or financial-aid award. Suppressed values remain `null`.

## Control evidence publication gate
For reviewed public/private records (`PUB`/`PRIV`), the importer now requires nonblank source `CONTROL` and checks it against the reviewed reporting population. A missing source control is not proof of public/private status and cannot be silently accepted. This gate does not independently verify campus setting, housing, accessibility, or career scores: those must be separately reviewed and attributed before publication.

## Unknown campus evidence
Reviewed records may use JSON `null` for unverified `setting` and `housing`; `null` is not equivalent to `false`. The browser labels these as unverified, allows unknown housing to remain visible under a housing-required filter with a prominent verification warning, and treats unknown campus setting as possible rather than confirmed preference points. Verify these fields from authoritative institutional sources before making definitive claims.

## Aid-category evidence
`aid: null` means aid categories have not been verified. `aid: []` means a reviewed source explicitly supports an empty list; neither should be inferred from the College Scorecard income-band net-price columns. The interface displays unverified aid separately from an empty category list. Actual grant and scholarship availability requires its own institutional source review.
