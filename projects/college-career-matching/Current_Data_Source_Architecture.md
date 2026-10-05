# Current Data Source Architecture

This document defines the preferred production data sources for the modern College + Career Matching Tool.

## Source hierarchy

| Layer | Preferred source | Role in model | Refresh approach |
| --- | --- | --- | --- |
| Institution + outcomes | U.S. Department of Education College Scorecard | Costs, admissions, completion, debt, earnings, institution and field-of-study outcomes | Refresh on Scorecard release |
| Institution + programs | NCES IPEDS | Institutional characteristics, enrollment, completions, awards, program inventory, NCES locale, housing/services | Annual |
| Affordability + aid detail | College Scorecard + IPEDS Cost/SFA | Cost of attendance, overall and income-band net price, grant/aid type prevalence and amounts | Release-specific; preserve survey/metric vintages |
| Community access | BTS National Transit Map + EPA Smart Location / Walkability | Transit-stop proximity and community walkability/location-efficiency evidence | BTS current snapshots; EPA vintage must remain explicit |
| Transfer + articulation | Authoritative state/system repositories; initial adapters: SUNY STEP and CUNY Transfer Explorer | Program pathways, agreements, course equivalencies, degree applicability, published transfer guarantees/conditions | Source-specific snapshots; preserve effective dates and conditions |
| Program taxonomy | NCES CIP | Standard program codes | Version-controlled taxonomy |
| Program ↔ occupation | NCES/BLS CIP–SOC Crosswalk | Many-to-many education-to-occupation bridge | Version-controlled crosswalk |
| Occupation taxonomy + work/worker characteristics | O*NET | Occupations, essential and transferable skills, software skills, knowledge, abilities, career interests, work activities/context, preparation, related occupations | Each O*NET production release |
| Employment outlook | BLS Employment Projections | Jobs, growth, annual openings, education/training, national outlook | Annual projection release |
| Current wages + geographic employment | BLS OEWS | Wage percentiles, employment, state/metro geography | Annual |
| Current job demand | Public job-posting sources | Titles, employers, skills, salary, work mode, location, recency | Frequent snapshot with capture date |
| Optional enrichment | Lightcast | Job postings, standardized skills, career pathways, employer/market enrichment | Only under current license |

## 1. College Scorecard

Use College Scorecard as the primary student-facing institution/outcome enrichment layer where available. The production adapter uses the official featured institution-level bulk ZIP rather than requiring an api.data.gov key. Direct download is preferred; when the federal bulk CDN blocks automated runners, the exact official ZIP can be supplied with `--source-file` and is still hashed, snapshotted, normalized, and QA-checked under the same source contract. CDN reachability is not treated as evidence that the dataset itself is unavailable.

Relevant categories include:

- institution identity and location;
- academics;
- admissions;
- costs and net price;
- student body;
- financial aid;
- completion and retention;
- earnings;
- debt and repayment;
- field-of-study outcomes.

Field-of-study Scorecard data can complement IPEDS program completions with outcome measures, but its cohort definitions and availability should remain visible in the explanation layer.

## 2. IPEDS

Use IPEDS for the institutional and program backbone:

- UNITID and institutional identity;
- sector/control;
- awards offered;
- enrollment;
- completions by CIP and award level;
- graduation/completion;
- finance and institutional characteristics as needed.

IPEDS is preferable to hand-entered institution descriptors because it is structured, downloadable, and maintained as the national postsecondary reporting system.

## 2A. Affordability, housing, setting, and accessibility

Use `AFFORDABILITY_HOUSING_ACCESSIBILITY_CONTRACT.md` as the semantic contract for the public explorer.

**Affordability:** show cost of attendance separately from average net price. Average net price is after federal, state/local, and institutional grants/scholarships and must not be confused with loans. Use the published income-band averages when a visitor supplies an income range; do not manufacture a family-size-specific estimate from institution-level aggregates.

**IPEDS survey structure:** account for the 2024–25 collection redesign. Cost-of-attendance and average-net-price items moved from the Student Financial Aid component into the Cost component; other financial-aid items remain in SFA. Adapters should therefore carry component/year provenance at field level rather than assuming one SFA file contains the whole affordability layer.

**Campus setting:** retain the full NCES locale code and derive the four-category City / Suburban / Town / Rural presentation without destroying the 12-category detail.

**Housing:** keep institutionally controlled housing availability, capacity, and the all-FTFT residency requirement distinct. A school with housing is not necessarily a school that requires housing. Roommate/private-room configuration is not a core federal field and should enter only as separately sourced school-level enrichment.

**Accessibility:** do not create one undocumented campus-accessibility score. Preserve at least these components separately:

- disability-services evidence reported through IPEDS, without treating registered-student share as a quality score;
- transit access derived from BTS National Transit Map stops/routes, with distance/mode evidence and vintage;
- walkability/location-efficiency evidence from EPA data with the dataset's older vintage made visible;
- optional OpenStreetMap physical-accessibility evidence only where tags are present, with missing tags treated as unknown rather than inaccessible.

Visitors may explicitly prioritize these components; no hidden default weights should be assigned.

## 3. Transfer and articulation

Treat transfer evidence as a separate, source-specific layer rather than an institution-level yes/no attribute. The initial implementation is New York public higher education because SUNY and CUNY expose current public transfer resources with useful program/course specificity.

Use authoritative sources in this order:

- SUNY Transfer Equivalency Platform (STEP): Transfer Agreement Inventory, Transfer Paths, core-course/path tools, and public course-equivalency resources;
- CUNY Transfer Explorer (T-Rex), Program Comparison, Universal Transfer Path evidence, and formal articulation resources;
- other state/system repositories as source-specific adapters are added;
- institution-published agreements/policies as lower-structure fallback evidence.

Keep **credit acceptance**, **course equivalency**, **major applicability**, **program articulation**, **admission guarantees**, and **standing** semantically distinct. A general transfer policy is not proof that a particular course advances a particular major. Preserve conditions such as minimum grades, program restrictions, effective dates, and source notes.

See `TRANSFER_ARTICULATION_LAYER_SPECIFICATION.md` for canonical tables, identity/CIP mapping rules, evidence hierarchy, QA gates, explanation contract, and implementation sequence.

## 4. CIP ↔ SOC bridge

Use the official NCES/BLS CIP–SOC Crosswalk as a **many-to-many relationship**, not a deterministic major-to-job lookup.

A program may map to several occupations; an occupation may map from several programs. The model should preserve that multiplicity and attach explanatory labels rather than presenting one career as the inevitable result of one major.

## 5. O*NET

Use O*NET as the occupational-content layer.

Recommended dimensions:

- occupation title/code;
- tasks;
- essential skills;
- transferable skills;
- knowledge;
- abilities;
- career interest types;
- work activities;
- work context;
- education, training, and experience;
- job zones;
- related occupations;
- software skills.

O*NET should drive the **career-interest / skill ↔ occupation** and **occupation ↔ adjacent occupation** logic.

## 6. BLS Employment Projections

Use BLS projections for:

- employment base;
- projected employment;
- numeric and percent change;
- annual openings;
- typical education needed for entry;
- related work experience;
- on-the-job training;
- national median wage reference.

These values are better suited to the career-outlook layer than proprietary historical growth fields.

## 7. BLS OEWS

Use OEWS for current occupational employment and wages at national, state, metropolitan, and nonmetropolitan levels.

The model should distinguish:

- **outlook** — future projections;
- **current labor-market level** — current employment/wages;
- **posting demand** — current advertised jobs.

Those are different signals and should not be collapsed into one number.

## 8. Public job demand

Use public job postings as a fast-changing demand layer rather than as the sole definition of the labor market.

Each posting record should retain:

- stable source ID where available;
- source URL;
- capture date;
- posting date;
- employer;
- title;
- location;
- work mode;
- salary range and salary period;
- extracted skills with the triggering source text;
- occupation mapping confidence.

Possible public sources include government/open-data job feeds and public institutional postings. The NYC Workforce Demand & Skills Signal project provides the initial schema and QA pattern.

## 9. Optional Lightcast enrichment

If a current Lightcast license is available, use it as an enrichment layer for:

- standardized postings;
- posting intensity;
- employer competition;
- posting duration;
- specialized/common/software skills;
- career pathways;
- program-market alignment.

The core matcher should still be able to run without Lightcast.

## Data-quality rules

Every production field should carry, directly or through its dataset:

- source;
- source version;
- observation/reference year;
- retrieval date;
- geography;
- unit;
- missingness status;
- transformation rule;
- confidence or quality flag where applicable.

## Recommendation layers

The modern matcher should not produce one opaque universal score. It should expose separate layers:

1. **College fit** — preferences and constraints.
2. **Affordability** — cost of attendance, overall/income-band average net price, grants/scholarships, loans, and outcomes kept semantically distinct.
3. **Academic/program fit** — program availability and structure.
4. **Transfer/pathway fit** — agreements, course equivalencies, major applicability, path guarantees, and explicit conditions.
5. **Admissions context** — descriptive selectivity and profile context, not a false certainty of admission.
6. **Career pathway fit** — CIP↔SOC pathways, skills/interests, outlook, wages.
7. **Current demand** — job-posting signals.
8. **Geographic & community fit** — institution/labor-market geography, NCES campus setting, transit access, walkability/location efficiency, and housing context.
9. **Accessibility evidence** — disability-services, transit, walkability, and physical-accessibility evidence shown separately with unknown states preserved.
10. **Explanation** — why each recommendation appears and what data influenced it.

## Current reference versions — October 2026

- **O*NET 31.0**, August 2026 production release.
- **BLS Employment Projections 2025–2035**, released August 27, 2026.
- **BLS OEWS May 2025**, released May 15, 2026.
- **College Scorecard institution-level technical documentation**, September 2025 version located during the architecture review.
- **2020 CIP ↔ 2018 SOC Crosswalk** remains the official NCES/BLS downloadable crosswalk identified in the current NCES CIP site.
- **SUNY STEP transfer resources**, current public pages reviewed October 4, 2026.
- **CUNY Transfer Explorer / 2026 articulation resources**, current public pages reviewed October 4, 2026.

These version labels should be updated as new official releases replace them.

## Next implementation step

Implement the SUNY Transfer Agreement Inventory adapter defined in `TRANSFER_ARTICULATION_LAYER_SPECIFICATION.md`, then establish transfer-layer institution-identity coverage and regression baselines before integrating transfer signals into recommendation calibration.
