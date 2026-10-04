# Career Pathway Optionality & Alignment Summary Contract

**Status:** executable program/candidate-level optionality summary implemented; thresholds and production scoring remain gated.

## Purpose

Summarize occupation-level career alignment back to a program or recommendation candidate without allowing one unusually attractive occupation to stand in for the whole program and without rewarding a program merely because its CIP maps to many SOC codes.

## Core principle

Career optionality is multidimensional evidence, not a scalar synonym for quality.

The initial summary therefore keeps separate:

- mapped pathway breadth;
- alignment-evidence coverage across pathways;
- median alignment;
- minimum and maximum observed alignment;
- interquartile range of alignment;
- mean preference-evidence coverage;
- optional count/share above a separately validated strong-alignment threshold;
- representative high-alignment occupations for explanation.

## Input

`career_pathway_alignment.csv` from the career-preference alignment layer, containing at minimum:

- `occ_code`
- `career_alignment_score`
- `career_alignment_coverage_rate`
- `career_alignment_status`
- candidate/program identity columns

An optional occupation-label table adds human-readable occupation titles.

## No pathway-count reward

`career_pathway_count` is descriptive. A program with 30 mapped occupations is not automatically preferable to one with 8. Crosswalk breadth can reflect classification structure as well as genuine optionality, and pathways differ in relevance and evidence quality.

Any later use of breadth in scoring requires explicit validation.

## Alignment distribution

Median is the initial central summary because it is less dominated by one extreme pathway. Min/max and IQR remain visible so heterogeneous programs are not represented as uniformly aligned.

These statistics describe the mapped occupation set; they do not estimate graduate outcome probabilities.

## Strong-alignment threshold

No threshold is hard-coded. If a validated/configured threshold is supplied, the tool reports:

- `strong_alignment_pathway_count`
- `strong_alignment_pathway_share`

Without a threshold, those fields remain empty. The code does not invent a definition of “strong.”

## Representative pathways

The tool may output a small deterministic set of high-alignment occupations, ordered by alignment, evidence coverage, and SOC code as a stable tie-break.

These are **examples for explanation**, not the program's only outcomes and not an aggregation rule. User-facing language should identify them as related/aligned pathways rather than promised careers.

## Evidence coverage

Two forms of coverage remain visible:

1. pathway coverage: share of mapped occupations for which an alignment score can be computed;
2. preference coverage: how much of the user's explicit preference evidence was observable within those pathways.

A program should not receive stronger confidence merely because missing evidence was ignored.

## Outputs

- `career_optionality_summary.csv`
- `career_representative_pathways.csv`
- `career_optionality_qa.json`

The summary can join the model-ready candidate feature table. The representative-pathway file feeds explanation/UI detail.

## Interpretation guardrails

Do not translate these fields into claims that a program guarantees career flexibility, employment, satisfaction, or earnings. CIP↔SOC remains a related-occupation crosswalk. O*NET preference alignment remains descriptive fit evidence. Labor-market outcomes remain separate dimensions.

## Next implementation block

Build the **education-to-career evidence bridge and feature registry** that joins program/candidate optionality summaries, labor-market summaries, transfer evidence, affordability, admissions context, and institutional/program evidence into named recommendation dimensions with source lineage. This registry should be the single declarative map between assembled raw features and the normalization/scenario pipeline, preventing ad hoc feature selection in later scoring work.
