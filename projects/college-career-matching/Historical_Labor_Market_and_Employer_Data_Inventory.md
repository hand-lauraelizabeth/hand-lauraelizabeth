# Labor-Market, Employer & Occupational Data Inventory

This inventory maps the data sources that can inform the career side of the College + Career Matching Tool. The materials fall into four different categories with different uses: licensed labor-market intelligence, institutional employer/job-system data, public occupational data, and private relationship/outcome records.

The modern matcher should keep those categories separate. A useful recommendation system needs current labor-market signals, but it should not depend on a static commercial report or expose institution-specific records.

## Source inventory

| Source | Data period | Useful fields / signals | Public-reuse posture | Role in modern matcher |
| --- | --- | --- | --- | --- |
| Lightcast program-overview collection | Q2 2023 reports; completions 2021; jobs 2020–2023; postings Oct. 2020–Jan. 2022 | CIP/program completions, tuition, target occupations, jobs, openings, earnings, growth, location quotient, employers, titles, skills, software, qualifications | Licensed/proprietary source material; use only within applicable Lightcast terms and attribution requirements | Design reference and, where separately licensed/current, optional commercial feed |
| Lightcast occupation overview | Q3 2024; employment 2022–2023; postings Jan. 2022–Dec. 2023 | employment, compensation, job-posting demand, industry distribution, employers, titles, demographics, CIP programs, completions | Licensed/proprietary | Design reference; replace with current public or authorized feeds |
| Lightcast Career Pathways | Q3 2024; postings Jul. 2023–Jun. 2024 | feeder/related occupations, advancement type, relevance, posting volume, salary difference | Licensed/proprietary | Useful model for occupation-to-occupation pathways; do not freeze historical values into recommendations |
| Lightcast Profile Analytics | Q3 2024; graduation years 2014–2024; profile activity since 2018 | cities, states, companies, occupations, titles, schools, specialized/common skills, qualifications | Licensed/proprietary and based partly on public online profiles | Methodological reference for program-to-career and skill signals |
| GSAS labor-market & program-alignment workbook | Primarily 2020–2023 Lightcast/Symplicity/LinkedIn-era data | degree/field, top employers, posting intensity, titles, target occupations, earnings, growth, LQ, job postings, employer partners, alumni profile fields | Mixed: licensed, institutional, and third-party/profile data | Architecture reference only; public model should not reproduce relationship/profile records |
| Employer-to-major engagement dataset | Updated 2024 | employer, industry, majors, relationship status, jobs posted, hires/offers, internships, engagement, outcomes, best-fit major | Institution-specific and contains contact/outcome information | Strong schema precedent for employer ↔ program ↔ outcomes; use only with authorized institutional data |
| Handshake production exports | 2024 | student/application/system activity | Private institutional records | Excluded from public matcher; only useful as evidence that an institutional deployment could accept authorized system inputs |
| O*NET data | Current official release is 31.0 (Aug. 2026) | occupations, tasks, skills, knowledge, abilities, work activities, technology skills, work context, education/training and related descriptors | O*NET 31.0 Database is CC BY 4.0 with required attribution and noted exceptions | Primary public occupational/skills source for the rebuild |

## Lightcast program-overview collection

The project files contain duplicate copies of a large Lightcast program-overview collection. Deduplication by filename yields **57 distinct program-report titles** spanning humanities, social sciences, quantitative fields, language/area studies, planning, biotechnology, and other graduate-program areas.

Representative reports identify themselves as **Lightcast Q2 2023 Data Set** reports produced in May 2023. Their structure is especially useful because a single report connects an academic program to:

- CIP codes and award levels;
- completions and institutional market share;
- tuition/fees and institution type;
- similar programs;
- target occupations;
- employment, openings, median earnings, growth, and location quotient;
- total and unique job postings;
- posting intensity and duration;
- top employers and job titles;
- specialized, common, and software skills;
- qualifications/certifications.

The reports also document their source stack. Institution data are drawn from IPEDS; occupation and wage estimates combine Lightcast/Emsi modeling with government sources including occupational employment statistics and the American Community Survey; state data can incorporate state labor agencies; and Lightcast job-posting data are collected and standardized from multiple posting sources.

This makes the reports valuable as a **schema precedent** for the new matcher: academic program → occupations → demand → employers → skills. The specific 2021–2023 values are not suitable for current recommendations.

## Q3 2024 occupation and pathway examples

A second set of reports provides a later example centered on urban and regional planning.

### Occupation Overview

The Q3 2024 occupation report connects an occupation to:

- employment and projected change;
- compensation;
- industries employing the occupation;
- posting demand, posting duration, and employers competing for talent;
- job titles;
- workforce demographics;
- related educational programs and CIP codes;
- program completions and schools.

### Career Pathways

The pathway report adds occupation-to-occupation relationships, distinguishing advancement and lateral pathways while showing relevance, posting demand, and salary differences. That is a useful conceptual model for the career matcher, although the new system should make pathway logic explainable and uncertainty-aware.

### Profile Analytics

The profile report connects an academic program to observed profile outcomes: geography, employers, occupations, titles, schools, skills, and qualifications. For a public tool, those relationships should be rebuilt from sources whose reuse terms and privacy posture fit the product rather than by reproducing individual profile data.

## GSAS labor-market and employer system

The `SOURCE - Labor Market and Program Alignment Background Research` workbook shows how multiple systems were brought together for program-to-market analysis.

### Lightcast-derived tabs

- **Top 10 Employers Per Major/Field** — degree, major/field, employer, total/unique postings, posting intensity, and median posting duration.
- **Top Posted Titles Per Major/Field** — degree, major/field, job-title posting metrics, plus target occupations with jobs, annual openings, earnings, growth, and location quotient.

### Symplicity-derived tabs

- **Current Job Postings** — title, employer, type, and posting recency.
- **Current Employer Partners** — employer, industries, geography, organization type, and size.

### Relationship and outcome layers

The workbook also contains a curated target-employer layer and a partial alumni/profile layer. Those demonstrate a useful analytical idea—combining market demand with existing relationships and observed outcomes—but are not appropriate as public-source tables because they include institution-specific and third-party profile information.

## Employer-to-major engagement dataset

`employer_data_with_majors_updated.v2.xlsx` provides a particularly strong schema for an institutional version of the matcher. Its fields connect:

- employer status and industry;
- majors and internal hubs;
- recent Handshake/Symplicity engagement;
- relationship start date;
- jobs posted;
- hires/offers;
- internships;
- career-fair and platform engagement;
- career outcomes and experiential learning;
- best-fit major.

The durable design idea is not the individual records. It is the **many-to-many relationship model**: an employer can connect to several majors, several kinds of engagement, and several observable outcomes. A future institutional deployment could ingest an authorized employer-system feed into that layer; a public version should use aggregated or public data instead.

## Handshake production exports

Several 2024 Handshake production exports are present for students and applications. They are deliberately outside the public project model. They contain person- and application-level institutional data and are neither necessary nor appropriate for demonstrating the public matching architecture.

The architecture should therefore support a clean separation between:

- **public mode** — public/open data plus user-provided preferences; and
- **institutional mode** — optional authorized system connectors with privacy, access, retention, and aggregation controls.

## O*NET data

An O*NET resources folder exists in the project materials, but it does not contain a reusable raw O*NET database extract. That is not a limitation for the rebuild: O*NET provides a current, versioned public database directly.

As of October 2026, the current production release is **O*NET 31.0 (August 2026)**. The downloadable database is available in Excel/CSV/JSON, relational database, and RDF formats, and O*NET Web Services provide access to the current database. Except for documented exceptions, O*NET 31.0 Database content is available under **CC BY 4.0** with attribution to the O*NET 31.0 Database and USDOL/ETA.

Official references:

- https://www.onetcenter.org/database.html
- https://www.onetcenter.org/db_releases.html
- https://www.onetcenter.org/license_db.html

O*NET is therefore a strong candidate for the occupational, task, skills, knowledge, abilities, work-activity, technology-skill, and education/training layers of the modern matcher.

## Licensing and publication boundary

Lightcast data and reports should be treated as licensed Content rather than as an open dataset. Lightcast's current general terms retain Lightcast's rights in Content, permit customer work product to incorporate limited elements under the applicable agreement, and require attribution for Lightcast Content used in reports or similar documents. The exact rights for any future use depend on the governing subscription/order terms.

Official reference:

- https://legal.lightcast.io/lightcast-legal/general-terms-of-service

For the public GitHub project, the practical rule is simple: **document the model and field architecture, not the proprietary bulk data**. Current commercial data can be added later only through an authorized feed with terms that support the intended use.

## Refreshability classification

| Class | Examples | Refresh approach |
| --- | --- | --- |
| **Direct public refresh** | O*NET; public government education/labor sources | Pull current version/API/download and record source version/date |
| **Authorized commercial refresh** | Lightcast job postings, profiles, skills-demand signals | Use only under an active license/API/data-share agreement |
| **Authorized institutional refresh** | Handshake/Symplicity employer, posting, outcome, and engagement data | Institution-controlled connector/export with privacy and aggregation rules |
| **Historical design reference** | 2023/2024 reports and workbook extracts | Preserve only as methodology/schema lineage; never treat as live market data |

## Implications for the matching model

The inventory supports a modern architecture in which:

1. college/program data and career data have independent source/version metadata;
2. CIP ↔ occupation mappings are many-to-many;
3. occupation ↔ skills relationships come from a refreshable taxonomy rather than static prose;
4. employer demand is a separate, time-sensitive signal rather than a permanent property of a major;
5. institutional relationships and outcomes can enhance recommendations when authorized, but are not required for the public model;
6. every market-sensitive field carries a source date or version;
7. commercial and private data can be swapped in or out without changing the core scoring model.

## Next step

The next design task is a **current-data refresh architecture**: assign an authoritative source, refresh cadence, identifier, and confidence/quality rule to each college, program, occupation, skill, affordability, outcomes, and labor-market field before implementing the contemporary scoring model.
