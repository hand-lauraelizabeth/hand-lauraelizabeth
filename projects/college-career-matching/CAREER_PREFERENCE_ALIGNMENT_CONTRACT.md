# Career Preference Alignment Contract

**Status:** pathway-level explicit-preference alignment implemented; scoring calibration remains gated.

## Purpose

Make the career side of the College + Career Matching Tool substantive. Programs should not be recommended merely because linked occupations have high wages or projected growth. The tool should be able to compare occupational pathways with what a user explicitly says they value in work.

## Grain

Alignment is calculated first at **occupation pathway** grain, not directly at institution or program grain. This preserves the fact that one program can connect to multiple occupations with different work characteristics.

## Inputs

### Program/candidate pathways
Must contain `occ_code`; may also carry `candidate_id`, `UNITID`, `program_id`, and `cip_code`.

### Occupation attributes
Long-form table:

- `occ_code`
- `attribute_id`
- `attribute_value`

Attributes may be drawn from appropriate O*NET domains such as interests, work values, skills, knowledge, work activities, work styles, or work context, provided source definitions/scales are retained upstream.

### Explicit career preferences

- `preference_id`
- `attribute_id`
- `target_value`
- `importance`
- `priority_explicit`
- optional `scale_min`, `scale_max`

Only `priority_explicit=true` rows participate.

## Scale compatibility

An alignment value is computed only when the preference and occupation attribute share a documented compatible numeric scale. The initial implementation uses normalized absolute distance:

`alignment = 1 - |occupation value - target value| / scale span`

clipped to `[0,1]`.

This is a transparent distance measure, not a probability of satisfaction or career success.

If compatible scale bounds are unavailable, alignment remains missing rather than inventing a normalization.

## Importance

Importance weights are user-supplied/approved preference importance values. The system does not invent importance weights for interests, skills, work values, or other attributes.

A pathway's current summary is the importance-weighted mean across observed explicit preferences. Coverage is reported separately.

## Missing evidence

Missing O*NET/occupation attribute evidence reduces `career_alignment_coverage_rate`. It does not become a mismatch score of zero.

A high alignment score with low coverage must not be presented with the same confidence as a similarly high score with broad evidence coverage.

## No earnings dominance

Wages and employment growth remain separate labor-market dimensions. They are not silently incorporated into career-preference alignment. If a user explicitly prioritizes earnings or growth, those preferences can be modeled separately and transparently.

## No deterministic career claim

CIP↔SOC establishes related pathways, not guaranteed outcomes. Alignment with an occupation does not establish that a program will place a student in that occupation, nor that the user will enjoy or succeed in it.

## Outputs

- `career_preference_alignment_detail.csv`: preference-by-pathway evidence and alignment
- `career_pathway_alignment.csv`: pathway-level score, evidence count, coverage, and status
- `career_preference_alignment_qa.json`

## Program-level use

The next aggregation step should retain multiple pathway perspectives rather than immediately averaging all occupations into one score. Useful summaries include:

- number/share of pathways with strong alignment under an explicitly validated threshold;
- median and range of pathway alignment;
- highest-alignment pathways shown by name as examples, not treated as the entire program;
- coverage across mapped occupations and explicit preferences;
- sensitivity to excluding individual preference domains.

Thresholds must be configured/validated, not invented in code.

## Next implementation block

Build the **career-pathway alignment summarizer and diversity/optionality layer**. It should summarize pathway-level alignment to the program/candidate grain while preserving career optionality: breadth of mapped occupations, breadth of well-aligned pathways when a validated threshold is supplied, dispersion of alignment, and the identities of representative pathways. It should avoid rewarding sheer pathway count without evidence quality and avoid treating a single excellent occupation match as proof that the entire program is an excellent career match.
