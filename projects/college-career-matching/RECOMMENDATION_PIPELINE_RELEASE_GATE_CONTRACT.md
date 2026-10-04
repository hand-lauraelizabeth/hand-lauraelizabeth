# Recommendation Pipeline Orchestration & Release Gate Contract

**Status:** fail-closed artifact release gate implemented. Full command orchestration and production authorization remain separate work.

## Purpose

Turn the growing set of source, modeling, validation, fairness, sensitivity, and explanation checks into a governed release boundary. A recommendation build should not be considered ready merely because a scoring script completed.

The release gate reads a declarative manifest of required QA artifacts and checks. It does not hard-code arbitrary acceptance thresholds.

## Pipeline stages

A complete recommendation build can include:

1. source ingestion and source QA;
2. institution/program/transfer/geography identity resolution;
3. candidate-universe construction and hard constraints;
4. feature assembly and registry validation;
5. pre-score evidence/missingness audit;
6. feature normalization;
7. within-dimension composition;
8. explicit-priority weight scenarios;
9. sensitivity/stability testing;
10. coverage/fairness diagnostics;
11. structured explanation generation;
12. explanation QA/rendering;
13. release gate.

Stages can have multiple artifacts. The first executable gate operates on JSON QA/summary artifacts; later orchestration can aggregate richer CSV diagnostics into stage-level JSON contracts.

## Gate manifest

Required columns:

- `stage_id`
- `artifact_path`
- `required`
- `check_path`
- `operator`
- `expected`

`check_path` is a dot-separated path into a JSON artifact.

Supported operators:

- `exists`
- `eq`
- `neq`
- `gte`
- `gt`
- `lte`
- `lt`

Numeric thresholds appear only in the manifest after they have been explicitly selected/validated. They are not embedded in the gate code.

## Fail-closed behavior

A required stage blocks when:

- its artifact is missing;
- its JSON is invalid;
- the configured check path is missing;
- the configured check fails.

Optional checks are reported but do not block the build.

This distinguishes a known optional limitation from a missing required validation stage.

## Release decision

The initial machine-readable decisions are:

- `BLOCKED`
- `ELIGIBLE_FOR_REVIEW`

`ELIGIBLE_FOR_REVIEW` deliberately does **not** mean production-approved. Human/model governance review, accessibility review, documented limitations, and any organizational release process still apply.

The gate should not emit `PRODUCTION_APPROVED` automatically.

## Example checks

Examples of checks that can be configured once their acceptance criteria are approved include:

- candidate-universe QA artifact exists;
- unresolved required review count equals zero;
- feature registry contains no missing required source columns;
- normalization QA reports no invalid reference ranges;
- all explicitly prioritized dimensions have usable values;
- sensitivity artifact exists and configured instability limits pass;
- coverage/fairness review has no unresolved blocking flags;
- explanation QA has no blocked material claims;
- accessibility validation is complete;
- source vintage/regression checks pass.

The contract intentionally does not assign numerical cutoffs for these examples.

## Outputs

- `recommendation_release_gate_detail.csv`: one row per configured stage/check with actual value, status, and failure reason;
- `recommendation_release_decision.json`: overall decision and blocked/optional counts.

## Audit rule

A release decision must be reproducible from:

- the gate manifest version;
- the referenced QA artifacts;
- source/model configuration versions;
- the code version/commit.

Changing a threshold or making a stage optional is therefore a policy change visible in the manifest, not an invisible code edit.

## Relationship to scoring

A successful score calculation is neither necessary nor sufficient for release. For an incomplete preference profile, the system may legitimately produce no ranking while still passing data/eligibility QA and presenting evidence. Conversely, a complete numerical ranking remains blocked if required validation or explanation stages fail.

## Next implementation block

Build the **pipeline runner/stage manifest** that invokes the existing modules in dependency order, records command/config/source versions, hashes key inputs/outputs, stops downstream scoring when prerequisite stages block, and assembles a single run manifest. Then add small synthetic fixtures and regression tests so the complete architecture can be exercised without confidential institutional data or waiting for the user's separate Power BI/synthetic-data work.
