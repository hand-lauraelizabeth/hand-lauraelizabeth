# College + Career Matching Tool — Coverage Universe Specification

The final matcher should begin from a **comprehensive universe of legitimate options** and narrow that universe according to the student's goals, constraints, and preferences. It should not begin from a prestige list, a commercial ranking, or a small set of schools and careers selected in advance.

## Institution coverage principle

The institution layer should aim to represent the full set of U.S. postsecondary institutions a prospective student could reasonably consider, subject to clear eligibility and data-quality rules.

At minimum, the production universe should include:

- public flagship universities;
- regional public universities;
- all campuses in state university and state college systems where represented as distinct institutions;
- public two-year and community colleges;
- prominent community colleges and transfer-oriented institutions;
- private nonprofit colleges and universities;
- historically Black colleges and universities;
- tribal colleges and universities;
- Hispanic-serving and other minority-serving institutions where relevant designations are available;
- women's colleges and other mission-specific institutions;
- accredited technical, professional, arts, and specialized institutions;
- other accredited institutions that offer credentials relevant to the student's stated goals.

The system should not exclude an institution merely because it is absent from a commercial ranking.

## Baseline institutional universe

### Primary backbone: IPEDS

Use the current IPEDS institutional universe as the main structured backbone because it provides stable UNITID identifiers and institution/program records suitable for joins.

The coverage build should retain institutions across sectors and award levels rather than filtering to four-year bachelor's institutions at ingestion.

Important dimensions include:

- institution control: public / private nonprofit / private for-profit;
- highest and predominant degree;
- two-year / four-year / less-than-two-year status;
- state and territory;
- campus/system identity where distinguishable;
- program availability;
- distance-education availability;
- open-admission/selectivity context;
- enrollment size;
- Carnegie/mission/context fields where available and useful.

### Accreditation validation

IPEDS participation and accreditation are related but not interchangeable concepts. The production pipeline should therefore maintain an **accreditation layer** rather than treating IPEDS presence alone as the accreditation test.

The final institution record should be able to distinguish:

- currently accredited;
- accreditation status unclear or unavailable;
- institution/program accreditation where a field requires it;
- closed/merged/inactive institutions retained only for historical continuity.

The accreditation source, accreditor, status, and retrieval/reference date should be traceable.

### College Scorecard

College Scorecard should enrich the institution universe with student-facing cost, admissions, completion, debt, and earnings information when available.

Absence from a Scorecard metric must not remove an otherwise legitimate institution from the universe. Missingness should affect confidence/context, not existence.

## Community-college and public-system coverage

Coverage QA should explicitly test public-system representation rather than assume it.

For every state and territory represented in the source data, produce counts for:

- public four-year institutions;
- public two-year/community colleges;
- other public institutions;
- private nonprofit institutions;
- other eligible accredited institutions.

The QA report should flag unexpectedly empty or implausibly small state/sector combinations for review.

The final interface should make community-college pathways first-class options, including:

- associate degrees;
- certificates;
- transfer pathways;
- articulation/transfer potential where authoritative data are available;
- lower-cost entry routes into bachelor's pathways;
- career/technical programs linked to occupations.

Community colleges should not appear only as fallback options after four-year schools.

## Specialized and nontraditional institutions

Do not flatten all schools into a single conventional residential four-year model.

Where data support it, preserve distinctions for:

- specialized arts/design institutions;
- conservatories;
- technical institutes;
- health-professions institutions;
- seminaries/religious institutions;
- primarily online institutions;
- adult-serving institutions;
- institutions with unusual calendar/delivery structures.

These characteristics should become filters and explanatory context, not automatic penalties.

## Institution inclusion and exclusion rules

### Include by default

A current institution should enter the candidate universe when it:

1. has a stable recognized institution identifier in the production source system;
2. is active/current in the applicable source release;
3. offers at least one postsecondary credential relevant to the matcher;
4. is not excluded by an explicit legal/status rule;
5. has sufficient identity metadata to avoid duplicate or ambiguous presentation.

### Do not pre-filter by

- U.S. News or other commercial ranking;
- selectivity;
- size;
- prestige;
- research intensity;
- four-year status;
- geographic proximity;
- user's current academic profile.

Those belong in later filtering/scoring or user preferences.

### Exclude or quarantine

- clearly closed/inactive institutions from the current recommendation universe;
- duplicate campus records that cannot be meaningfully distinguished;
- institutions whose accreditation/authorization status cannot be resolved when accreditation is required for the intended use;
- records that represent administrative/system entities rather than student-enrolling institutions, unless intentionally surfaced as system context.

Quarantined records should remain auditable rather than being silently deleted.

## Career coverage principle

The career universe should likewise be comprehensive.

The production baseline should include:

- all current detailed O*NET occupations;
- all compatible detailed BLS occupations used for projections/wages;
- occupations with low current posting volume;
- public-sector occupations;
- education, arts, humanities, nonprofit, care, trades, technical, scientific, and professional careers;
- emerging and changing occupations where the source system supports them.

The system should not restrict recommendations to occupations with the highest wages, fastest growth, or largest posting volume.

## Career taxonomy and granularity

Maintain both:

- detailed ONET_SOC_CODE for occupational content;
- normalized/base SOC6 for BLS and cross-source joins.

Where one BLS SOC maps to multiple O*NET detailed occupations, preserve the detail rather than collapsing prematurely.

Career-path suggestions should distinguish:

- direct CIP↔SOC pathways;
- adjacent/related occupations;
- skill-similar occupations;
- career progression/pathway relationships;
- current posting-demand signals.

These are different relationship types.

## Career coverage QA

For every O*NET release, record:

- total detailed occupations;
- count mapped to base SOC;
- count with BLS projections;
- count with OEWS wage/employment data;
- count connected to at least one CIP through the official crosswalk;
- count with no direct CIP mapping;
- count with essential/transferable/software skill data;
- count with related-occupation data.

Unmapped occupations should remain visible as coverage gaps, not disappear from the career universe.

## Program coverage

The education layer should retain the full current six-digit CIP program taxonomy represented in institutional completions/program data.

For every institution, preserve all relevant credential levels rather than reducing the institution to a single "major list."

Coverage reporting should include:

- institutions with at least one active program;
- CIP6 programs by award level;
- programs with direct CIP↔SOC mappings;
- programs without direct mappings;
- fields with Scorecard field-of-study outcomes;
- fields whose outcome data are missing/suppressed.

## Coverage metrics

Every production build should generate a coverage report with, at minimum:

### Institutions

- total active candidate institutions;
- institutions by state/territory;
- institutions by control;
- institutions by award/sector level;
- public two-year/community-college count;
- public four-year count;
- private nonprofit count;
- accreditation-status coverage;
- percentage with College Scorecard enrichment;
- percentage with program/completions data;
- percentage with cost/outcome fields.

### Careers

- total detailed O*NET occupations;
- BLS projection match rate;
- OEWS national wage match rate;
- state/metro wage coverage where used;
- CIP↔SOC linkage coverage;
- skill-data coverage;
- current-posting coverage.

### Programs

- total institution-program-award combinations;
- distinct CIP6 count;
- crosswalk coverage;
- Scorecard field-of-study enrichment coverage.

## User-facing consequence

Comprehensiveness does **not** mean showing every option at once.

The interface should begin from the broad universe and then use:

- hard constraints;
- user-selected filters;
- explainable preference weights;
- affordability;
- program availability;
- admissions context;
- geography;
- career alignment;
- confidence/data completeness

to narrow and rank results.

A student should be able to discover a strong-fit state school, community college, specialized institution, or less nationally prominent college even when it would never appear on a conventional "top schools" list.

## Implementation status

The coverage-first ingestion work is substantially implemented. Completed layers include the full current IPEDS directory/completions baseline, DAPIP accreditation bridging, state/sector coverage reporting, explicit community-college pathway coverage, the full O*NET 31.0 occupation universe, BLS projections and national OEWS joins with unmatched occupations retained, career/program coverage reports, and live-observed regression floors that fail closed when a refresh materially shrinks coverage.

Remaining coverage work is narrower and should build on these layers rather than replace them:

1. **Resolve system/campus/administrative duplicates** while preserving legitimately distinct campuses and auditable source identities.
2. **Run College Scorecard enrichment** once credentials are available; Scorecard absence must never remove an otherwise eligible IPEDS institution.
3. **Expand OEWS geography** from the validated national baseline to state/metropolitan/nonmetropolitan coverage where the matcher needs local labor-market context.
4. **Add authoritative transfer/articulation data** so associate-to-bachelor pathways can be represented directly.
5. **Build the integrated model-ready join layer** and promote recommendation scoring only after its QA and explanation/provenance requirements pass.


## Live coverage verification

The ingestion pipeline should verify the full IPEDS institution and completions feeds directly rather than testing only handpicked institutions. A live CI smoke path exercises both the current institution directory and 6-digit CIP completions source so schema changes or unexpected filtering are caught before coverage logic is built on top of them.
