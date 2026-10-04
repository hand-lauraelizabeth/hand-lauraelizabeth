# College + Career Matching Tool

This project develops a modern, explainable college-and-career matching system from an earlier college-selection model built in 2017.

The historical model is useful because it already contains several ideas that remain valuable:

- user-entered academic profile data;
- adjustable preference weights;
- institution-level characteristics;
- academic, social, and quality-of-life factors;
- Reach / Target / Safety logic;
- separate ranking streams for overall fit and admissions category;
- explicit tie-breaking;
- program-strength rationales;
- transparent spreadsheet formulas rather than an opaque recommendation score.

The current project does **not** treat the 2016–2017 admissions, ranking, cost, or program data as current. Those fields will be rebuilt from authoritative sources before the tool is used for contemporary recommendations.

## Historical lineage

| Version | Date | Role |
| --- | --- | --- |
| **SchoolsProjectV25_toupdate.xlsx** | July 18, 2017 | Base V25 branch |
| **LEHrationales.xlsx** | July 18, 2017 | Program-strength rationale layer for majors/fields |
| **SchoolsProjectV25_toupdateLEH7-20.xlsx** | July 20, 2017 branch | Expanded school-data and scoring work |
| **SchoolsProjectV25_toupdateLEH7-28wbusiness.xlsx** | July 28, 2017 | Latest located historical branch; adds undergraduate-business ranking fields |
| Google Sheets copies imported later | 2024–2026 | Access/analysis copies of the historical workbook, not new model versions |

The July 28 workbook is the reference point for reconstructing the historical architecture.

## Historical workbook architecture

The primary Data sheet spans **155 columns (A:EY)** and combines four layers in one sheet:

1. **User inputs** — test scores and preference settings.
2. **Institutional data** — admissions, cost, enrollment, academic ratings, rankings, programs, deadlines, and related attributes.
3. **Normalization and scoring** — derived values translating raw attributes and user preferences into comparable terms.
4. **Output ranking** — overall fit plus Reach, Target, and Safety lists with explicit tie-breaking.

Additional sheets include:

- **Rationales** — program-level qualitative rationales;
- **Colleges and Majors** — college/major reference material.

## User-input model

The historical input block includes:

| Input | Historical scale |
| --- | --- |
| SAT Critical Reading | 0–800 |
| SAT Mathematics | 0–800 |
| ACT | 0–36 |
| Private ↔ Public preference | 1–5 |
| National university ↔ Liberal arts college preference | 1–5 |
| Urban ↔ Rural preference | 1–5 |
| Small ↔ Large enrollment preference | 1–5 |
| Ranking / exclusivity importance | 1–5 |
| Academics importance | 1–5 |
| Social importance | 1–5 |
| Quality of life importance | 1–5 |

The model therefore separates **student profile** from **student preference**, which is a useful design principle for the new system.

## Major historical data groups

The institution table includes fields for:

- school identity, address, website, and location type;
- public/private status;
- total and undergraduate enrollment;
- SAT/ACT ranges and derived midpoint values;
- financial aid, student loans, debt, applicants, acceptance, enrollment, retention, and graduation;
- academics, social, and quality-of-life ratings;
- admissions contacts and application requirements;
- strongest programs and overlap schools;
- early/regular admission dates;
- tuition and fees;
- U.S. News, business, engineering, teaching, Forbes, QS, Times Higher Education, and ARWU rankings;
- location and acceptance-rate reference fields;
- program rationales in a companion workbook.

These sources and values are historical and must be replaced rather than refreshed in place.

## Scoring architecture

The formula layer begins by converting test-score differences into normalized SAT/ACT values, then combines those with acceptance rate to estimate separate admissions-category scores.

At a high level:

**student profile** → SAT / ACT distance from institutional ranges → normalized score → acceptance-rate weighting → Reach / Target / Safety admissions scores

In parallel:

**student preferences** → institution attributes → preference-distance / importance adjustments → overall fit score

The two streams are then combined:

- **Overall fit** = preference-based score.
- **Reach result** = preference score + Reach admissions score.
- **Target result** = preference score + Target admissions score + category rules.
- **Safety result** = preference score + Safety admissions score + category rules.

Separate ranking blocks then produce ordered Overall, Reach, Target, and Safety lists.

## What should be preserved

The modern model should preserve:

- explainable scoring;
- adjustable user weights;
- distinction between academic admissibility and personal fit;
- explicit uncertainty;
- multiple recommendation categories rather than one universal ranking;
- qualitative program rationales alongside quantitative scoring;
- traceable sources and dates;
- visible tie-breaking and ranking logic;
- ability to inspect why a recommendation changed.

## What should be redesigned

The following historical features should **not** be carried forward uncritically:

- fixed coefficients in the Reach/Target/Safety formulas;
- rankings treated as direct proxies for quality;
- star-count academic/social/quality-of-life fields;
- binary or narrow encodings for institution type and geography;
- admissions logic based on outdated standardized-testing assumptions;
- deterministic thresholds that do not communicate uncertainty;
- historical cost, acceptance, testing, and deadline data;
- race/demographic fields without a clear contemporary use case and governance rationale;
- major-strength narratives without current sourcing and structured metadata.

## Modern target architecture

The new system will separate the model into explicit layers:

1. **Student goals & constraints**
2. **College/institution data**
3. **Programs/majors**
4. **Career/occupation data**
5. **Skills and interests**
6. **Affordability and outcomes**
7. **Admissions uncertainty**
8. **Preference-weighted fit**
9. **College-to-career crosswalk**
10. **Explanation layer**

The career layer will use program-to-occupation relationships as **probabilistic pathways**, not deterministic major-to-job mappings.

## Next development stage

The next stage is to inventory the historical Lightcast/O*NET/employer/system datasets, then define:

- authoritative current data sources;
- field-level refresh cadence;
- CIP ↔ SOC ↔ skill crosswalks;
- missing-data rules;
- uncertainty controls;
- validation and bias checks;
- user-adjustable weights and sensitivity testing.

See [Historical Formula Specification](Historical_College_Model_Formula_Specification.md) for the scoring logic extracted from the 2017 workbook.
