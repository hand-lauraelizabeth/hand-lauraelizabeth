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

## Data-source architecture

The career-side source inventory now distinguishes open occupational data, licensed labor-market intelligence, institution-specific employer systems, and private relationship/outcome data.

- [Labor-Market, Employer & Occupational Data Inventory](Historical_Labor_Market_and_Employer_Data_Inventory.md)
- [Labor-Market & Employer Data Dictionary](Labor_Market_and_Employer_Data_Dictionary.md)
- [Historical Formula Specification](Historical_College_Model_Formula_Specification.md)
- [Historical Data Dictionary](Historical_College_Model_Data_Dictionary.md)

## Comprehensive coverage requirement

- [Coverage Universe Specification](COVERAGE_UNIVERSE_SPECIFICATION.md) — institution, program, and career inclusion rules plus coverage-regression requirements. The matcher begins from a broad legitimate universe rather than a prestige list.

## Public interactive experience

The visitor-facing interaction model is now represented in [public-explorer.html](public-explorer.html) and on the portfolio site. It is intentionally different from a developer demo:

- useful results are visible on first render;
- ordinary preference controls are immediately available;
- hard filters update the visible set without a submit/run step;
- soft priorities create an explainable fit ordering only after the visitor explicitly selects them;
- no account, installation, notebook, terminal, or local runtime is required;
- up to three programs can be compared inline;
- the entry mode can be broad, career-first, college/program-first, compare-known, transfer, or returning-student without forcing a wizard;
- career-first mode can use a governed selected labor market and keeps current labor-market evidence separate from long-term occupational outlook;
- result cards, candidate detail, and comparison can show structured related career pathways with governed occupation titles when available, while treating pathway count as descriptive rather than a quality score;
- career-first result cards can also preview current selected-market employment/wage evidence beside long-term projection evidence, including unavailable states, governed market labels, and source vintage; those occupation-level measures are not converted into browser-side scores and are not presented as graduate earnings or placement rates;
- when a visitor explicitly prioritizes current labor-market context or long-term outlook, the service emits traceable priority-context or evidence-gap explanations; raw wage/growth values do not manufacture positive reasons or negative tradeoffs;
- those priority explanations can be expanded inline to inspect the exact supporting SOC/occupation rows, geography, source vintage, evidence states, measures, and stable evidence IDs without opening the full candidate-detail panel;
- full mapped pathways remain separate from future reviewed preference-aligned representative pathways;
- readable example content remains available without JavaScript;
- all current records are explicitly fictional demonstration data until the governed current-data release is production-ready.

The `prototype/` directory remains a service-contract harness for exercising `/metadata`, `/options`, `/match`, candidate detail, and comparison semantics. It should not be treated as the primary public UX.

## Prototype status

The federal-source ingestion and coverage prototype is now exercised end to end for the unauthenticated production sources. Current live baselines include **5,985 IPEDS directory records across 59 states/territories**, **313,566 C2025_A completion rows**, **6,097 CIP↔SOC relationships**, and the complete **1,016-occupation O*NET 31.0 occupation table**.

Program coverage now removes **20,708 IPEDS CIP 99.0000 summary rows** from specific-program analysis, leaving **273,404 institution + CIP6 + award-level combinations across 5,811 institutions**. The build observes **1,617 distinct specific CIP6 codes**; **1,616** have a direct relationship in the official CIP 2020 ↔ SOC 2018 crosswalk. Missing direct mappings remain visible coverage gaps rather than exclusions or quality penalties.

The career join baseline contains **867 unique O*NET base SOC6 codes**, with **819** matching detailed BLS 2025–2035 projection occupations (**94.46%**) and **818** matching the May 2025 national OEWS detailed occupation set (**94.35%**). O*NET detail is preserved even where a base SOC is unmatched.

The institution/accreditation build retains **5,985 institutions**, matches **5,713** to at least one DAPIP identifier, and identifies **1,049 public community-college-pathway candidates** through the explicit sector/institution-category/Carnegie proxy. That proxy includes **823 public two-year sector records** and recovers **225 public four-year-sector institutions** with associate-oriented pathway signals; it is not treated as a legal or mission designation.

All three live coverage layers—**institution/accreditation, program, and career**—now have conservative regression floors in [coverage_baselines.json](coverage_baselines.json). The opt-in live CI gates fail if a future source refresh silently falls below those floors. On October 4, 2026, a combined live run passed all three gates.

The pipeline supports timestamped raw snapshots, source hashes and metadata, normalized CSV outputs, QA reports, coverage reports, dry-run source resolution, and a keyless College Scorecard bulk-file adapter. The adapter targets the official June 10, 2026 institution-level ZIP and can ingest either a direct download or a user-supplied copy of that same official ZIP. GitHub-hosted Actions currently receives HTTP 403 from the Scorecard bulk CDN, so CDN reachability is treated as a transport probe rather than a core QA gate.

See [Reproduce the Data Build](RUNBOOK.md) for the executable workflow.

## Ingestion & QA infrastructure

The source layer is now defined in both human-readable and machine-checkable form:

- [Reproduce the Data Build](RUNBOOK.md) — commands for dry runs, public-source ingestion, keyless College Scorecard bulk-file ingestion, and live smoke testing;
- [Production source manifest](source_manifest.json) — pinned source IDs, releases, access URLs, canonical keys, required artifacts, metadata, and join cardinalities;
- [Coverage regression baselines](coverage_baselines.json) — conservative live-observed minimums for institution, program, and career coverage;
- [Ingestion contract](INGESTION_CONTRACT.md) — raw → staging → normalized → model-ready rules, key normalization, suppression handling, and refresh behavior;
- [QA & Join Tests](QA_JOIN_TESTS.md) — source-level, cross-source, coverage-regression, and recommendation-gating acceptance criteria;
- [MVP Field-Level Source Matrix](MVP_Field_Level_Source_Matrix.md) — 89 fields mapped to source variables, joins, cadence, transformations, and missing-data behavior;
- [Machine-readable source matrix](MVP_Field_Level_Source_Matrix.csv) — CSV for ingestion/configuration work.

The repository CI validates manifest structure, source IDs, join references, CIP↔SOC cardinality, production-source privacy boundaries, source-matrix consistency, and coverage-baseline configuration.

## Next development stage

The integrated model-ready institution → program → occupation layer is now implemented, including source lineage, conservative institution-identity review clusters, preservation of unmatched programs/occupations, and regression gates. The next work should extend that validated layer rather than create another parallel prototype:

1. ingest and validate a current College Scorecard bulk snapshot through the keyless official-file adapter when the federal CDN is reachable (or from a user-supplied copy of that same official ZIP), using Scorecard only as enrichment rather than as an institution-inclusion filter;
2. add authoritative transfer/articulation information so community-college-to-bachelor pathways can be represented directly rather than inferred from sector or taxonomy alone;
3. expand OEWS beyond the national baseline to state, metropolitan, and nonmetropolitan geography where local labor-market context materially improves matching;
4. review identity clusters against authoritative system/campus crosswalks where available, while keeping distinct UNITIDs distinct by default and never collapsing on fuzzy names;
5. only after those enrichment layers pass QA, begin recommendation-scoring calibration while keeping admissions context, preferences, affordability, career alignment, and data completeness as separate explainable signals.

Recommendation scoring remains gated; the model-ready build is validated, but current Scorecard enrichment, transfer evidence, and scoring calibration are not yet production-complete.


See the:
- [Historical Formula Specification](Historical_College_Model_Formula_Specification.md) for the scoring logic;
- [Historical Data Dictionary](Historical_College_Model_Data_Dictionary.md) for the 147 named fields across the 155-column Data sheet;
- [Historical Labor-Market & System Data Inventory](Historical_Labor_Market_and_System_Data_Inventory.md) for Lightcast, Symplicity, Handshake, employer/program, and synthetic data lineage;
- [Current Data Source Architecture](Current_Data_Source_Architecture.md) for the preferred public production stack;
- [MVP Field-Level Source Matrix](MVP_Field_Level_Source_Matrix.md) — 84 source, user-input, and derived fields mapped to authoritative datasets, join keys, refresh cadence, transformations, and missing-data rules;
- [Machine-readable source matrix](MVP_Field_Level_Source_Matrix.csv) — CSV version for future ingestion/configuration work;
