# National college search — standardized-test provenance and source expansion

**Current implemented dataset (2026-10-11):** Exact U.S. Department of Education College Scorecard institutional ZIP from 2026-06-10, originally uploaded by the owner to the private Google Drive `College + Career Matcher — Official Data Sources` folder. SHA-256 verified against the pinned national source manifest: `f56a181b000ca4914e924c16b6b81dcc656e25aeb2ac68ab7d271ac0f29ffd58`.

The published national directory retains **6,243 currently operating institutions** (CURROPER=1) keyed by UNITID. The separately fetched source-specific score overlay contains **1,199 institutions** with at least one SAT/ACT metric:

| Measure | Reported institutions | Not reported in the 6,243-universe |
| --- | ---: | ---: |
| SAT_AVG | 1,037 | 5,206 |
| ACTCMMID | 970 | 5,273 |
| Complete SATVR25/50/75 + SATMT25/50/75 | 949 | 5,294 |
| Complete ACTCM25/50/75 | 920 | 5,323 |

The Scorecard release date is **2026-06-10**; test score reporting cohort is **Fall 2024**. Source per tile: U.S. Department of Education · College Scorecard / IPEDS admissions · Fall 2024 · direct source link. Each column is **nullable**, and absent/masked/not-applicable values are never zero-imputed.

**Reproducible local build:** `python build_scorecard_scores_verified.py --archive /path/to/Most-Recent-Cohorts-Institution_06102026.zip --output data/sprint3/college-search-scores.v2.json`. The original 23,559,465-byte ZIP is never committed publicly. The derived overlay is 92,137 bytes raw and 16,051 bytes gzip, so combined with the national v3 gzip (259,736 bytes) the total is **275,787 bytes / 269.3 KiB**, below the 750 KiB compressed budget (768,000 bytes). The original CSV file has 6,273 rows; 30 not marked currently operating are intentionally excluded.

## Classification method and guardrails

The user may enter a SAT total (400–1600) and/or ACT composite (1–36) as an **optional reference**. School filters independently compare user-selected ranges against **SAT_AVG** and **ACTCMMID**; default-wide ranges are inactive. When all three school percentiles exist, a voluntarily entered score is described as **below the source-based reference range**, **within the source-based reference range**, or **above the source-based reference range**. These are descriptive comparisons with enrolled score submitters, not admissions categories, likelihoods, thresholds, or cutoffs. SAT total boundaries are estimates derived from section percentiles, not reported SAT composite percentiles; ACT composite percentile boundaries are reported. All labels link to a qualification note. When SAT and ACT disagree, no single combined badge appears. Badges are absent if no personal score is provided or source evidence is incomplete. Institution-specific current testing policies are **unknown** in this overlay; applicants must check each school directly.

The SAT total boundaries are explicitly labeled **estimates** because they sum separately reported SAT reading and mathematics 25th/50th/75th percentiles. Summing section quantiles does not yield the exact quantiles of the SAT-total distribution. ACT composite percentiles are the directly reported values. Scores reflect **enrolled first-time students submitting results**, not the entire applicant pool, admitted nonenrollees, or test-optional students who did not submit.

## Source expansion (ordered by evidence relevance, not search ranking)

1. **Federal Scorecard longitudinal institution-level archives**, matching UNITID and genuine original survey cohort, especially the all-years institution data ZIP 1996–97 through 2025–26. Only add a prior year as *clearly historical* evidence when the newest-year field is unavailable; never silently show a 2016-era SAT on the current 1600 scale without verification. Include release/cohort on every tile.
2. **NCES IPEDS Data Center / reported admissions collection**, using unit-level SAT/ACT 25th/50th/75th percentile and test-policy indicators for the relevant year. Use direct institution/year URL where possible. Because Scorecard often republishes IPEDS measures, **deduplicate** rather than counting the same survey twice.
3. **Official university/college Common Data Set or admissions information**: prefer newer explicit composite SAT percentiles when available, preserve the source school's URL, PDF section/page or HTML anchor and admitted/enrolled cohort definitions; support additional policy notes such as test optional, superscoring, or test blind. Do not overwrite valid official Scorecard data merely because a newer-looking page has a different denominator.
4. **TOEFL / English proficiency:** institutional language-proficiency *minimum requirements* and exemptions are program- and applicant-dependent. Do **not** conflate with institution-level entrant score distributions or classify admissions likelihood solely from TOEFL. Collect TOEFL iBT minimum, test date/version, program/applicant applicability, exemptions, source URL, and year; enable a separate optional filter only after review.
5. **NCES Digest and College Board national/state trends:** useful **contextual benchmarking only**. Never use state or cohort aggregates in an individual school's percentile distribution. Third-party compilations may guide discovery but must trace each retained figure to its original official report.

## Minimum fields for a supplementary source row

`unitid`, `exam`, `cohort_year`, `p25`, `p50`, `p75`, `source_provider`, `source_dataset`, `source_url`, `source_kind` (federal / NCES / institutional), `verified_on`, `sat_score_scale` (when relevant), `reporting_population`, `test_optional_policy` (if evidence exists), `review_state`. Store fields separately for SAT and ACT and retain original raw source values in a nonpublic research log. Schema v2 `source_registry` plus record-specific SAT/ACT source IDs is already supported by the browser.

**Release scope:** Separate draft WordPress staging page **1164** carries the verified v2 overlay and score-range UI. Existing published WordPress page 1044 is intentionally unchanged pending explicit promotion review. Local Chromium/Playwright testing of the branch checks 390px and 1440px widths, live card source displays, category bounds, old city/cost/sort functionality, Clear and responsive overflow.

## Source references

- https://collegescorecard.ed.gov/data/
- https://collegescorecard.ed.gov/data/glossary/
- https://nces.ed.gov/ipeds/reported-data/
- https://nces.ed.gov/ipeds/use-the-data

**Remaining genuine coverage gap:** the school-level source may lack SAT/ACT because admissions do not require those tests or because of masking/nonreporting; not every missing value can or should be backfilled from other sources. Record nonapplicability explicitly only with supporting evidence. The private Google Drive source archive is available; to ingest older years, first locate/import the comprehensive all-years Scorecard archive or selected year-specific original ZIPs, preserving their hashes and source URLs.
