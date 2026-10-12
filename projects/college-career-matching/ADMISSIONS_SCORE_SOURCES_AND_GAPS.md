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

## October 11, 2026: authoritative all-years archive incorporated

Owner's existing Google Drive folder `College + Career Matcher — Official Data Sources` contains a newly uploaded **469,515,074-byte** `College_Scorecard_Raw_Data_06102026 (1).zip`. The entire ZIP was programmatically materialized and its SHA-256 verified: `bfe3add63069fea1fa61c8b910bfaef9d29baa3ae68702e6595b04d2023293a1`. It holds annual files `MERGED1996_97_PP.csv` through `MERGED2025_26_PP.csv` as well as field-of-study and crosswalk files.

**New live-branch data file:** `data/sprint3/college-search-scores.v3.json` (still a review branch, **not deployed on the public WordPress page**). Based on the official fall-2024 score overlay, it backfills two recently preceding admissions cohort files **only when the corresponding SAT or ACT exam has no usable current-year field**: `MERGED2023_24_PP.csv` (fall 2023) and `MERGED2022_23_PP.csv` (fall 2022). Never combine an average from one year with percentiles from another year within the same exam. Do not fill from the 2025–26 archive file, whose admissions fields are NA. The 2017–2021 years remain longitudinal *research only* at present; Scorecard actual reported 50th percentiles are not available in those files, and SAT scale/format transitions require care.

| Metric | Current-only v2 | Historical-enriched v3 |
|---|---:|---:|
| Institution rows with any SAT/ACT data | 1,199 | **1,247** |
| Reported SAT average | 1,037 | **1,164** |
| ACT composite midpoint or historical **reported ACTCM50 median** | 970 | **1,015** |
| Complete estimated SAT total 25th/50th/75th bands | 949 | **1,051** |
| Complete ACT composite reported 25th/50th/75th bands | 920 | **965** |

**Change statistics:** 172 exam-specific additions to 146 existing/new UNITIDs; 48 newly represented schools. The fall-2023 source contributes 70 SAT and 29 ACT additions, while fall 2022 contributes 57 SAT and 16 ACT. A historically anomalous composite SAT percentile spread above 500 points is withheld from categorization; its otherwise available reported SAT average may remain visible. These are federal *reported* data, not third-party extrapolations.

All v3 source entries carry provider, source dataset/file, URL, release, historical flag, cohort, and pinned source checksum. The user-facing tiles label `Historical SAT` / `Historical ACT` and the specific fall cohort; for historical ACT the reference score is **ACTCM50 (reported median)**, not the older ACTCMMID midpoint. SAFETY/TARGET/REACH* are only conventional comparisons for complete percentile sets, remain explicitly nonpredictive, and flag historical evidence in the badge accessibility label. Missing scores remain null.

The all-years ZIP is **not** committed to public GitHub; `build_scorecard_history_overlay.py` reproduces the augmented dataset from the two private official ZIPs and base v2. The derived v3 overlay is **100,024 bytes raw, 17,945 bytes gzip**. Combined with the existing 259,736-byte national catalog gzip, the **277,681-byte total** remains below the 750 KiB cap. [GitHub Actions integration and mobile/desktop browser regression PASSED](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/38196856343).

The WordPress **private draft 1164** references this verified v3 dataset and the current review-branch script; the public page 1044 is unchanged. The historical backfill is a **recent-cohort enrichment, not complete historical scoring**. Future work: analyze all annual observations for dedicated trend views without putting older score observations into default college matching, and research official university Common Data Set/IPEDS reports for institutions still missing percentile ranges.

## Classification method and guardrails

The user may enter a SAT total (400–1600) and/or ACT composite (1–36) as an **optional reference**. School filters independently compare user-selected ranges against **SAT_AVG** and **ACTCMMID**; default-wide ranges are inactive. For classification only, if all three school percentiles exist, an applicant score lower than 25th percentile is **REACH**, 25th–75th inclusive is **TARGET**, higher than the 75th percentile is **SAFETY**. Because this is merely a score-position shorthand, all labels carry `*` linking to a prominent qualification note and are *not* admission likelihood estimates. When SAT and ACT disagree, no single combined badge appears. Badges are absent if no personal score is provided or source evidence is incomplete.

The SAT total boundaries are explicitly labeled **estimates** because they sum separately reported SAT reading and mathematics 25th/50th/75th percentiles. Summing section quantiles does not yield the exact quantiles of the SAT-total distribution. ACT composite percentiles are the directly reported values. Scores reflect **enrolled first-time students submitting results**, not the entire applicant pool, admitted nonenrollees, or test-optional students who did not submit.

## Source expansion (ordered by evidence relevance, not search ranking)

1. **Federal Scorecard longitudinal institution-level archives**, matching UNITID and genuine original survey cohort, especially the all-years institution data ZIP 1996–97 through 2025–26. Only add a prior year as *clearly historical* evidence when the newest-year field is unavailable; never silently show a 2016-era SAT on the current 1600 scale without verification. Include release/cohort on every tile.
2. **NCES IPEDS Data Center / reported admissions collection**, using unit-level SAT/ACT 25th/50th/75th percentile and test-policy indicators for the relevant year. Use direct institution/year URL where possible. Because Scorecard often republishes IPEDS measures, **deduplicate** rather than counting the same survey twice.
3. **Official university/college Common Data Set or admissions information**: prefer newer explicit composite SAT percentiles when available, preserve the source school's URL, PDF section/page or HTML anchor and admitted/enrolled cohort definitions; support additional policy notes such as test optional, superscoring, or test blind. Do not overwrite valid official Scorecard data merely because a newer-looking page has a different denominator.
4. **TOEFL / English proficiency:** institutional language-proficiency *minimum requirements* and exemptions are program- and applicant-dependent. Do **not** conflate with institution-level entrant score distributions or classify admission SAFETY/TARGET/REACH solely from TOEFL. Collect TOEFL iBT minimum, test date/version, program/applicant applicability, exemptions, source URL, and year; enable a separate optional filter only after review.
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
