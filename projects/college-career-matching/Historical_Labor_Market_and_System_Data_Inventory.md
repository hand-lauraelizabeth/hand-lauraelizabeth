# Historical Labor-Market, Employer & System Data Inventory

This inventory documents the data families available to inform the College + Career Matching Tool. It separates reusable model structure from data that is historical, licensed, private, or synthetic.

## Data-use tiers

| Tier | Purpose | Examples | Public matcher use |
| --- | --- | --- | --- |
| **A — Public / refreshable** | Core production data | O*NET, BLS, IPEDS, College Scorecard, public job data | Yes |
| **B — Licensed / proprietary** | Enrichment and historical design reference | Lightcast reports and extracts | Only with current rights/license |
| **C — Private institutional** | Model validation and feature discovery | Symplicity, Handshake, employer/contact and student/outcome exports | Aggregated/de-identified validation only |
| **D — Synthetic / demonstration** | Testing, portfolio demonstration, QA | Synthetic labor-market and program-alignment workbooks | Yes |

## 1. Lightcast / Emsi labor-market data

### Located materials

Two Drive folders titled **Lightcast Data** contain a large collection of program-overview reports, including undergraduate, master's, and doctoral programs across humanities, social sciences, STEM, area studies, and interdisciplinary fields.

Additional Lightcast-derived materials include:

- **Top 10 Employers Per Major/Field — Lightcast 2020–2023**
- **Top Posted Titles Per Major/Field — Lightcast 2020–2023**
- **Occupation Overview** reports
- **Career Pathways** reports
- **Program Overview** reports

### Fields and signals represented

Across the located reports and research sheets, Lightcast data provide:

- CIP-coded programs and completions;
- target occupations;
- employment levels and growth;
- annual openings;
- median earnings;
- location quotient;
- total and unique job postings;
- posting intensity;
- median posting duration;
- employers posting for a field;
- posted job titles;
- specialized skills;
- common skills;
- software skills;
- qualifications/certifications;
- feeder and advancement occupations;
- career-path relevance;
- advertised salary differences;
- industry concentration;
- age and demographic workforce profiles;
- top schools by completions.

### Located vintages

- **Q2 2023** program reports use, depending on the report, completions around 2021, jobs around 2020–2023, and postings around Oct. 2020–Jan. 2022.
- **Q3 2024** occupation/pathway reports include 2022–2024-era employment and posting windows.
- A GSAS research workbook summarizes major/field-specific Lightcast employer and title signals for **2020–2023**.

### Design value

These files show a strong model for connecting:

**program / CIP → occupations → openings / wages / growth → employers / titles → skills → adjacent career pathways**.

That chain should be preserved in the modern architecture.

### Use boundary

Lightcast is treated as a licensed/proprietary enrichment source rather than the public production core. Historical reports can inform schema and feature design, but their values should not be silently refreshed, bulk-republished, or assumed to remain current.

## 2. O*NET

A Drive folder titled **ONET Resources** is present but currently contains no files. That does not create a dependency because O*NET is publicly reacquirable and should be ingested fresh rather than reconstructed from an old local copy.

The modern matcher should use O*NET for occupational:

- titles and codes;
- tasks;
- knowledge;
- skills;
- abilities;
- work activities;
- work context;
- education/training/experience;
- job zones;
- interests;
- related occupations;
- technology skills where available.

## 3. GSAS labor-market and program-alignment research

The workbook **SOURCE - Labor Market and Program Alignment Background Research** contains eight distinct data areas:

1. LinkedIn GSAS Alumni Profile
2. Top 10 Employers Per Major/Field — Lightcast 2020–2023
3. Target Employers
4. Top Posted Titles Per Major/Field — Lightcast 2020–2023
5. Basic Sorted Categories Current Job Postings — GSAS
6. Current Job Postings — GSAS
7. Current Employer Partners — GSAS
8. Current+Grads — Partial LinkedIn Pull GSAS (05/23)

This is particularly useful as evidence that the historical work already combined labor-market demand, field-of-study alignment, employer targeting, live postings, existing employer relationships, and alumni/current-student outcome signals.

### Public-use treatment

- Lightcast-derived aggregates → Tier B.
- Raw Symplicity jobs/employer partners → Tier C.
- LinkedIn profile-level records → Tier C.
- The combined schema and analytical method → reusable.

## 4. Hostos employer ↔ major / engagement data

The workbook **employer_data_with_majors_updated.v2.xlsx** contains an employer-to-program relationship model with fields including:

- employer status;
- career hub / cluster;
- majors;
- engagement level;
- employer;
- industry;
- relationship start date;
- recent jobs posted;
- known hires/offers;
- internships hosted;
- experiential-learning activity;
- career-fair / system engagement;
- student-favorite counts;
- career outcomes;
- best-fit major.

It also contains named contacts, email addresses, student names, and other private institutional information.

### Design value

The reusable idea is an **employer ↔ major/program ↔ engagement/outcome** relationship layer. The raw workbook should remain private; a modern production model should use public employer/job data or de-identified institutional aggregates.

## 5. Handshake system exports

Located exports include application and student datasets from October–November 2024.

### Application export fields include

- student identifiers and contact fields;
- application status;
- employer and job details;
- job skills;
- location and work mode;
- salary ranges;
- job type;
- student major;
- timestamps and application counts.

### Student export fields include

- student identity and contact information;
- academic information;
- GPA;
- document-review activity;
- advising/event records;
- document metadata;
- appointment descriptions and notes;
- program/major information;
- engagement counts.

### Use boundary

These are **Tier C: private institutional data**. They are valuable for understanding real career-system schemas and for testing aggregate model logic, but raw records should not enter a public matcher or public repository.

## 6. Symplicity / career-services system data

Located materials include:

- raw current job-posting exports;
- raw employer-partner exports;
- employer contact lists;
- career-outcome / advising reports;
- employer engagement fields embedded in the employer-major workbook;
- historical activity/reporting workbooks.

These files contain combinations of student information, employer contact data, advising activity, employment status, salary/wage fields, and institutional engagement metrics.

### Design value

They demonstrate useful operational entities:

**student / learner → program → career service activity → application → job → employer → outcome**

and

**employer → industry → program fit → engagement → postings → internships → hires**.

Those relationships belong in the conceptual model; the raw private records do not.

## 7. Synthetic labor-market portfolio work

The workbook **Case Study - Labor Market & Program Alignment Analytics (Synthetic)** contains:

- Market Demand;
- Skills Signals;
- Partnership Gaps;
- Dashboard.

This is Tier D and can be used freely for demonstration, regression testing, UI prototyping, and explanation-layer design.

## 8. Public workforce-demand project specification

The **NYC Workforce Demand & Skills Signal** project already defines a public-data schema for job-posting analysis with fields for employer, title, location, work mode, salary, domain, skills/tools, reproducibility signals, data-quality signals, and source/capture dates.

This can supply the **current-demand / job-posting** layer of the eventual matcher without relying on private Handshake or Symplicity exports.

## Reusable entity model

The historical data imply a modern relational model with these principal entities:

- `institution`
- `program`
- `program_completion`
- `occupation`
- `occupation_skill`
- `occupation_outlook`
- `program_occupation_crosswalk`
- `employer`
- `job_posting`
- `posting_skill`
- `career_pathway`
- `student_profile` / user-entered profile
- `student_preference`
- `fit_score`
- `recommendation_explanation`

Private institutional entities such as identifiable student records, advising notes, private contacts, and individual outcomes should remain outside the public production data model.

## Main conclusion

The historical work is substantially richer than a college-ranking spreadsheet. It already connects **education, labor-market demand, employers, postings, skills, career pathways, and student outcomes**. The modern rebuild should preserve those relationships while replacing historical/licensed/private values with current public data wherever possible.
