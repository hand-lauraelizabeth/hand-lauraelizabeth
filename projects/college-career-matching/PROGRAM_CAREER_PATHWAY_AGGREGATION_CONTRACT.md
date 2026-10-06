# Program → Career Pathway Aggregation Contract

**Status:** executable descriptive aggregation implemented; production scoring remains gated.

## Purpose

Translate the official many-to-many CIP↔SOC relationship into usable program/candidate evidence without pretending that a program has one inevitable occupation or that the occupation with the highest wage is representative of the program.

## Unit of evidence

The fundamental record remains a **program × occupation pathway**:

`UNITID + program_id + CIP + SOC`

When a recommendation candidate is available, `candidate_id` is carried through so institution-local labor-market evidence can be attached at candidate × occupation grain.

## Required inputs

- program inventory: `UNITID`, `program_id`, `cip_code`
- normalized official CIP↔SOC crosswalk: `cip_code`, `occ_code`
- occupation evidence: unique `occ_code` plus selected national/projection/O*NET measures

Optional:

- candidate table: `candidate_id`, `UNITID`, `program_id`
- local evidence: unique `candidate_id + occ_code`

## Many-to-many semantics

CIP↔SOC is a pathway crosswalk, not an observed placement distribution. Therefore:

- each mapped SOC remains visible;
- no SOC is designated the program's primary outcome without a separate authoritative basis;
- the crosswalk does not supply probabilities or shares;
- an occupation's wage is not a graduate earnings estimate;
- an occupation's employment projection is not a forecast that a particular graduate will obtain that occupation.

## Descriptive aggregation

For each numeric occupation measure the initial summary reports:

- number of pathways with observed evidence;
- evidence coverage rate across mapped pathways;
- median;
- minimum;
- maximum.

The range is retained to expose heterogeneity, not to reward the maximum. The model must not substitute `max` for a program value.

Future aggregation methods may add weighted summaries only when a defensible weight source exists (for example, observed program-to-occupation outcomes with appropriate rights/governance). Equal-pathway weighting should not be mislabeled as an observed employment distribution.

## Missing and suppressed evidence

Suppressed/missing occupation measures are excluded from descriptive numeric calculations but remain reflected in `observed_n` and `coverage_rate`. They are not converted to zero.

A program with no official SOC mapping receives `no_soc_mapping`; this is not automatically negative career evidence.

Likewise, an occupation absent from local OEWS publication cannot be interpreted as zero local employment or zero demand.

## National, projection, and local evidence remain distinct

The feature layer should preserve distinctions among:

- national current employment/wages;
- BLS long-term projections;
- state/local OEWS employment/wages;
- O*NET occupation characteristics;
- later observed demand/outcome evidence.

They measure different things and should not be blended into an unexplained labor-market score upstream.

## Outputs

- `program_career_pathway_evidence.csv`: pathway-level evidence retained for explanations/audit
- `program_career_pathway_summary.csv`: descriptive program/candidate summaries
- `program_career_pathway_qa.json`: counts, summarized measures, aggregation rule

## Product-facing pathway identity

The product enrichment may carry a structured pathway list containing `soc_code` and, when supplied by governed occupation evidence, `occupation_title`. SOC remains the canonical identity. Missing titles remain null/code-only rather than being guessed, and conflicting nonblank titles for the same SOC fail the enrichment bridge.

The browser may preview related pathway titles/codes, but it must label them as related occupations rather than outcomes. The complete mapped set is separate from any later representative/high-alignment subset.

## Recommendation use

The descriptive summary can feed the feature assembler and normalizer, but the pathway-level file remains the source for user-facing statements such as the occupations connected to a program and the breadth/uncertainty of labor-market evidence.

No statement should imply that CIP↔SOC alone proves employment outcomes.

## Next implementation block

Build the **career-preference alignment layer**. Rather than ranking programs only by wages/growth, connect explicit career interests and work-value/skill preferences to SOC/O*NET evidence, preserve multiple occupations per program, and calculate transparent pathway-level alignment before any program-level summary. This is also where the College + Career tool begins to connect the user's career side of the profile to the education side without collapsing the two into a prestige or earnings ranking.
