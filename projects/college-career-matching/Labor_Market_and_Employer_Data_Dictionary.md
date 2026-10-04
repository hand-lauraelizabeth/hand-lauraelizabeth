# Labor-Market & Employer Data Dictionary

This dictionary summarizes the reusable field structure found across the labor-market, program, employer, and career-system materials that inform the College + Career Matching Tool.

It describes the schema without reproducing licensed bulk data, employer-contact details, student records, or individual profile records.

## 1. Lightcast program-overview reports

Representative source vintage: **Lightcast Q2 2023 Data Set**.

### Report parameters

| Field family | Examples | Model use |
| --- | --- | --- |
| Program | CIP code, program name | Program identifier / crosswalk key |
| Geography | state / region | Market scope |
| Institution | institution name | Institution-program join |
| Award level | master's, doctorate, etc. | Program-level filter |
| Time window | completions year, jobs timeframe, postings timeframe | Recency/version control |

### Education supply

| Field | Model use |
| --- | --- |
| Completions | Program supply / scale |
| Program market share | Relative program scale |
| Institution type | Institutional context |
| Distance / non-distance delivery | Modality |
| Award level | Credential pathway |
| Tuition & fees | Affordability context |
| Similar programs | Program-neighborhood / alternative pathways |

### Target occupations

| Field | Model use |
| --- | --- |
| Occupation | Career node |
| Jobs | Employment scale |
| Annual openings | Opportunity flow |
| Median earnings | Compensation signal |
| Growth | Direction / momentum |
| Location quotient | Regional concentration |

### Job-posting market

| Field | Model use |
| --- | --- |
| Total postings | Hiring activity |
| Unique postings | De-duplicated demand |
| Posting intensity | Recruitment-effort / duplication signal |
| Employers competing | Employer breadth |
| Median posting duration | Time-to-fill / posting persistence signal |
| Top employers | Employer demand |
| Top job titles | Role demand / title normalization |

### Skills and qualifications

| Field | Model use |
| --- | --- |
| Specialized skill | Occupation/program skill signal |
| Common skill | Transferable skill signal |
| Software / technology skill | Tool requirement |
| Frequency in postings | Demand prevalence |
| Frequency in profiles | Observed supply prevalence |
| Qualification / certification | Credential signal |
| Postings with qualification | Credential demand |

## 2. Lightcast occupation-overview reports

Representative source vintage: **Lightcast Q3 2024 Data Set**.

| Field family | Fields / measures | Model use |
| --- | --- | --- |
| Occupation identity | occupation code, occupation name | Career identifier |
| Geography | national / state / region | Market context |
| Employment | jobs by year, change, percent change | Employment trend |
| Compensation | hourly / annual median | Earnings |
| Industry mix | industry, share of occupation | Employer-sector pathways |
| Posting activity | unique postings, monthly demand, duration | Hiring demand |
| Employers | top companies, posting counts | Employer opportunity |
| Titles | top job titles, posting counts | Search/title normalization |
| Demographics | age, race/ethnicity, gender | Descriptive workforce context; not a fit score by default |
| Programs | CIP code, program, completions | Program-to-occupation linkage |
| Schools | institution, completions | Education supply context |

## 3. Lightcast Career Pathways

| Field | Model use |
| --- | --- |
| Focus occupation | Starting career node |
| Related occupation | Adjacent career node |
| Pathway category | Advancement / lateral pathway |
| Relevance | Strength of relationship |
| Average unique monthly postings | Demand signal |
| Mean salary difference | Economic transition signal |

## 4. Lightcast Profile Analytics

| Field family | Fields / measures | Model use |
| --- | --- | --- |
| Program parameters | CIP/program, education level, graduation-year range | Cohort definition |
| Profile count | Number of matching profiles | Denominator / coverage |
| Geography | city, state, count, percent | Geographic outcomes |
| Companies | company, count, percent | Employer outcomes |
| Occupations | SOC occupation, count, percent | Program-to-occupation pathways |
| Job titles | title, count, percent | Observed role outcomes |
| Schools | school, count, percent | Education provenance/context |
| Specialized skills | skill, prevalence | Skill outcomes |
| Common skills | skill, prevalence | Transferable skill outcomes |
| Qualifications | certification/license, count | Credential outcomes |

## 5. GSAS labor-market & program-alignment workbook

### Top employers by major/field

| Field | Meaning |
| --- | --- |
| Degree | Credential level |
| Major / field | Academic program |
| Employer | Employer name |
| Total postings | Raw posting count |
| Unique postings | De-duplicated posting count |
| Posting intensity | Total-to-unique ratio |
| Median posting duration | Posting persistence |
| Existing relationship indicator | Whether an employer relationship existed in the institutional system |

### Top posted titles by major/field

| Field | Meaning |
| --- | --- |
| Degree | Credential level |
| Major / field | Academic program |
| Job title | Market-facing role title |
| Total / unique postings | Demand counts |
| Posting intensity | Recruitment intensity |
| Median posting duration | Posting persistence |
| Target occupation | Occupation mapping |
| Jobs | Employment scale |
| Annual openings | Opportunity flow |
| Median earnings | Compensation |
| Growth | Employment trend |
| Location quotient | Regional concentration |

### Symplicity job-posting layer

| Field | Meaning |
| --- | --- |
| Title | Job title |
| Employer | Employer / location label |
| Type | Full time, internship, part time, etc. |
| Posting time | Recency marker |

### Symplicity employer-partner layer

The raw export stores employer records in concatenated text. Recoverable attributes include:

- employer name;
- industry / industries;
- geography;
- organization type;
- organization size.

### Alumni/profile layer

The profile table contains fields for identity, current organization and role, geography, industry, seniority/job function, education, profile links, and connection metadata. These are **restricted relationship/profile fields**, not public matcher inputs.

## 6. Employer-to-major engagement dataset

`employer_data_with_majors_updated.v2.xlsx` contains **30 columns**:

| # | Field | Model role | Public model? |
| ---: | --- | --- | --- |
| 1 | STATUS | Relationship state | Aggregated only |
| 2 | HUBS | Internal program/career grouping | Institution-specific |
| 3 | MAJORS | Major/program relationship | Yes, if generalized |
| 4 | Recent Engagement through Handshake/Symplicity | Relationship recency | Authorized institutional mode |
| 5 | Employer | Employer node | Yes where public/authorized |
| 6 | Website | Employer identifier/context | Yes where public |
| 7 | Full Name | Contact identity | No |
| 8 | Contact Type | Relationship/contact classification | Aggregated only |
| 9 | Primary Contact Email | Contact detail | No |
| 10 | Industry | Employer sector | Yes |
| 11 | Relationship Started | Relationship tenure | Authorized institutional mode |
| 12 | Jobs Posted Last 2 Years | Demand/engagement | Aggregated or authorized |
| 13 | Known Hires/Offers Last Two Years | Outcome signal | Aggregated or authorized |
| 14 | CODE | Internal classification | Map before reuse |
| 15 | Internships Hosted Last 2 Years | Experiential opportunity | Aggregated or authorized |
| 16 | Partnerships For Success 2022 | Program participation | Institution-specific |
| 17 | Partnerships For Success 2023 | Program participation | Institution-specific |
| 18 | Monthly Engagement: Career Fairs | Employer engagement | Aggregated or authorized |
| 19 | Symplicity Monthly Engagement: Career Outcomes | Employer/outcome engagement | Authorized institutional mode |
| 20 | May Monthly Engagement: EL Placements Created | Experiential-learning activity | Authorized institutional mode |
| 21 | Monthly Engagement: Symplicity Employer Contact Logins | Platform engagement | Authorized institutional mode |
| 22 | Non-Experiential Monthly Learning Applications Shared through Symplicity | Application activity | Authorized institutional mode |
| 23 | Monthly Engagement: Non-EL Job Postings | Job-posting activity | Aggregated or authorized |
| 24 | Student Favorite Count | Student-interest signal | Aggregated only |
| 25 | Career Outcome: Employer(count) | Outcome count | Aggregated or authorized |
| 26 | Experiential Learning: Employer(count) | Experiential count | Aggregated or authorized |
| 27 | Student Name for Hires | Person-level outcome | No |
| 28 | Title for Hires | Observed role outcome | Aggregated/generalized |
| 29 | Notes | Unstructured relationship context | No by default |
| 30 | Best Fit Major | Curated program-employer relationship | Generalize/validate before reuse |

## 7. Handshake production exports

The project files include 2024 production exports for students and applications. Their person-level contents are excluded from the public architecture.

For a future institutional mode, the relevant **classes of fields** are:

- student/program identifiers;
- application activity;
- employer/job identifiers;
- event or engagement activity;
- outcome/status fields;
- timestamps.

Any implementation using these data would require institution-controlled authorization, purpose limitation, aggregation, retention rules, and access controls.

## 8. O*NET® data

No raw historical O*NET database extract is needed for the rebuild because the official O*NET database is versioned and directly refreshable.

The modern data dictionary should pull the relevant current O*NET tables during the refresh-architecture stage. Candidate families include:

- occupation data;
- alternate titles;
- tasks;
- skills;
- knowledge;
- abilities;
- work activities;
- work context;
- interests and work values where appropriate;
- education, training, and experience;
- technology skills and tools;
- related occupations.

O*NET 31.0 Database content is generally available under CC BY 4.0, subject to the documented license exceptions and attribution requirements.

## 9. Core identifiers for the rebuild

The modern matcher should normalize around stable identifiers rather than names alone:

| Entity | Preferred identifier family |
| --- | --- |
| Institution | IPEDS UNITID |
| Academic program | CIP code + award level + institution |
| Occupation | SOC / O*NET-SOC code |
| Skill | O*NET element / technology-skill identifier or source-specific skill ID |
| Employer | Canonical employer ID within the chosen source, plus normalized name |
| Geography | FIPS / standard region identifier where available |
| Time | source version + observation period + retrieval date |

These identifiers provide the join layer needed for the next stage: current-source mapping and refresh cadence.
