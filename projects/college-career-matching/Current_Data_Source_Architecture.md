# Current Data Source Architecture

This document defines the preferred production data sources for the modern College + Career Matching Tool.

## Source hierarchy

| Layer | Preferred source | Role in model | Refresh approach |
| --- | --- | --- | --- |
| Institution + outcomes | U.S. Department of Education College Scorecard | Costs, admissions, completion, debt, earnings, institution and field-of-study outcomes | Refresh on Scorecard release |
| Institution + programs | NCES IPEDS | Institutional characteristics, enrollment, completions, awards, program inventory | Annual |
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

## 3. CIP ↔ SOC bridge

Use the official NCES/BLS CIP–SOC Crosswalk as a **many-to-many relationship**, not a deterministic major-to-job lookup.

A program may map to several occupations; an occupation may map from several programs. The model should preserve that multiplicity and attach explanatory labels rather than presenting one career as the inevitable result of one major.

## 4. O*NET

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

## 5. BLS Employment Projections

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

## 6. BLS OEWS

Use OEWS for current occupational employment and wages at national, state, metropolitan, and nonmetropolitan levels.

The model should distinguish:

- **outlook** — future projections;
- **current labor-market level** — current employment/wages;
- **posting demand** — current advertised jobs.

Those are different signals and should not be collapsed into one number.

## 7. Public job demand

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

## 8. Optional Lightcast enrichment

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
2. **Affordability** — cost/net price/debt/outcomes.
3. **Academic/program fit** — program availability and structure.
4. **Admissions context** — descriptive selectivity and profile context, not a false certainty of admission.
5. **Career pathway fit** — CIP↔SOC pathways, skills/interests, outlook, wages.
6. **Current demand** — job-posting signals.
7. **Geographic fit** — institution and labor-market geography.
8. **Explanation** — why each recommendation appears and what data influenced it.

## Current reference versions — October 2026

- **O*NET 31.0**, August 2026 production release.
- **BLS Employment Projections 2025–2035**, released August 27, 2026.
- **BLS OEWS May 2025**, released May 15, 2026.
- **College Scorecard institution-level technical documentation**, September 2025 version located during the architecture review.
- **2020 CIP ↔ 2018 SOC Crosswalk** remains the official NCES/BLS downloadable crosswalk identified in the current NCES CIP site.

These version labels should be updated as new official releases replace them.

## Next implementation step

Build a field-level source matrix for the MVP: each desired matcher field → authoritative source → source variable → join key → geography → update cadence → transformation → missing-data behavior.
