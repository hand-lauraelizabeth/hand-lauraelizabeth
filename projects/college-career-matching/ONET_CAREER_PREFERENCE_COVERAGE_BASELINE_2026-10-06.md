# O*NET Career Preference Coverage Baseline — 2026-10-06

**Status:** live official-source baseline established; reviewed career-preference evidence is descriptive and service-gated.

## Sources and run

Live validation workflow: GitHub Actions run **37471003189**, completed successfully on 2026-10-06.

- O*NET Database 31.0, August 2026.
- O*NET `work_activities.csv` SHA-256: `6c266205b2926c0c854a7a577aae29fe492c71bb0df7e197adca830b58fe4ea1`.
- Combined O*NET 31.0 configured-source SHA-256: `49dcc684cbf6b55aa4f612b0e1792d444c90e2222c62c8fd91ece21c65187c40`.
- CIP 2020 ↔ SOC 2018 crosswalk SHA-256: `ba3d59a191b9d977a5c457a66b9348c4f2f7963aafacf72c0b80113b46bf0ab8`.

## O*NET reviewed-preference artifact

The official O*NET 31.0 Work Activities table contained **74,702 rows across 911 rated occupations**. The governed preference adapter retained only the three approved Work Activity Importance attributes and only `.00` base occupation profiles.

Observed normalized artifact:

- approved attributes: **3**
- normalized reviewed rows: **2,286**
- unique `.00` base SOC6 profiles: **762**
- observed reviewed rows: **2,286**
- suppressed reviewed rows: **0**
- not-relevant reviewed rows: **0**
- missing reviewed rows: **0**

Every retained base profile therefore has observed values for all three reviewed attributes in this release.

## CIP↔SOC pathway coverage

The official crosswalk produced:

- CIP↔SOC relationship rows: **6,097**
- distinct CIP6 codes: **2,143**
- distinct SOC6 codes: **868**

Reviewed O*NET `.00` evidence covers:

- SOC6 with a reviewed base profile: **762 / 868 = 87.788%**
- SOC6 with all three reviewed attributes observed: **762 / 868 = 87.788%**
- CIP↔SOC relationships with all three reviewed attributes observed: **5,013 / 6,097 = 82.221%**
- SOC6 without a reviewed `.00` base profile: **106**
- SOC6 with a base profile but partial/non-observed reviewed evidence: **0**

All three approved questions have the same observed coverage in O*NET 31.0 because each retained `.00` profile has all three Work Activity Importance values.

## Interpretation

The 106 uncovered SOC6 codes are **coverage gaps**, not low-fit occupations. The service must not substitute a specialty `.01/.02/…` profile, average specialties into a parent SOC, or assign zero alignment.

A program may therefore have mapped career pathways for which work-characteristic alignment is unavailable even when other career evidence such as BLS outlook or OEWS wages is present. Pathway alignment coverage must remain visible separately from the alignment index.

## Regression floors

`coverage_baselines.json` intentionally uses conservative floors below the observed values:

- at least 750 SOC6 with reviewed base profiles;
- at least 87% distinct-SOC coverage;
- at least 4,900 covered CIP↔SOC relationship rows;
- at least 81% relationship coverage;
- no more than 120 crosswalk SOC6 without a reviewed base profile;
- exactly three approved reviewed attributes.

These are source-regression guards, not recommendation-quality thresholds. A future O*NET or crosswalk release that legitimately changes taxonomy/coverage requires deliberate review rather than silently inheriting the old baseline.

## Product boundary

The normalized `career_preference_attributes.csv` is a required O*NET ingestion artifact and can be supplied to `service_host.py` through `CCX_CAREER_ATTRIBUTES` or `--career-attributes`. The service advertises only approved attributes actually present in that artifact.

This baseline does not authorize production activation and does not make career-preference alignment part of recommendation ranking.
