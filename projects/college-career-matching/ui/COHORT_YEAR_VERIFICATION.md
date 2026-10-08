# Income-band net-price cohort verification (publication blocker)

Status: **UNVERIFIED for the June 10, 2026 institution extract**. No real institutional records may be approved for publication until this is resolved.

## Source-of-truth procedure

1. Retrieve the current official College Scorecard Data Dictionary from the Department of Education data-documentation page: https://collegescorecard.ed.gov/assets/CollegeScorecardDataDictionary.xlsx
2. Inspect **`Most_Recent_Inst_Cohort_Map`** for the latest institution extract, and cross-check **`Institution_Cohort_Map`** for the annual archive. Do not substitute the field-description worksheet or the overall net-price glossary.
3. For each field family `NPT41_PUB` through `NPT45_PUB`, `NPT41_PRIV` through `NPT45_PRIV`, `NPT41_PROG` through `NPT45_PROG`, and `NPT41_OTHER` through `NPT45_OTHER`, identify the reporting cohort aligned with the June 10, 2026 latest institution extract.
4. Record dictionary edition/date, cohort-map sheet name and cell/row references, metric cohort, and whether every applicable population shares that cohort.
5. Compare against the official institution-level technical documentation; document exceptions and distinguish collection year, award year, and academic year.
6. Only after this review, populate `net_price_reference_year` in reviewed metadata, set `publication_approved: true` following independent review, and run validation and CI.

## What existing sources establish

- The official technical documentation defines income-band net price and the five family-income brackets, and notes that the underlying IPEDS Student Financial Aid and Institutional Characteristics components can cover different periods.
- The Scorecard glossary labels **overall** `NPT4_PUB` and `NPT4_PRIV` as 2023–24 award-year cohorts in its current indexed text. This does **not** prove that every `NPT41`–`NPT45` field in the June 2026 archive uses the same cohort.
- The official API documentation warns that different metrics have different reporting years and directs readers to the cohort-map worksheets.

## Branch locations and source restrictions

Keep 20 eight-digit New York branch/location identifiers outside the six-digit institution import. Do not infer a six-digit parent from a shared prefix without independent evidence. The 397 six-digit New York institution candidates and 20 branch/location candidates remain `DO_NOT_PUBLISH`.

## Verification record (fill only from reviewed source)

| Item | Value |
| --- | --- |
| Official dictionary URL | https://collegescorecard.ed.gov/data/data-documentation/ |
| Dictionary edition and retrieval date | PENDING |
| Latest-file cohort map | `Most_Recent_Inst_Cohort_Map` — cell references PENDING |
| Annual-file cross-check | `Institution_Cohort_Map` — cell references PENDING |
| NPT41–NPT45 applicable population/cohort mapping | PENDING |
| Exceptions and methodology notes | PENDING |
| Independent reviewer and approval date | PENDING |
| Publication status | DO_NOT_PUBLISH |

## Retrieval contingency
The official September 2025 institution technical documentation points to the `/assets/CollegeScorecardDataDictionary.xlsx` path, which currently returns HTTP 403 in this environment. The previous `/files/` URL should not be treated as authoritative. The current official XLSX download may return an access error. If so, request the current release dictionary from the Scorecard help desk (`scorecarddata@rti.org`) and retain the response or downloaded file with its release date and SHA-256. An older archived dictionary can clarify methodology and sheet structure but **must not** be used as proof of the June 2026 metric cohort. The full June 2026 all-data ZIP may contain the dictionary even when the institution-only ZIP does not; verify its archive member list before relying on it. Never substitute a third-party estimate for an official cohort map.
