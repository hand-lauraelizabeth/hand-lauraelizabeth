# Recommendation Pipeline Runner & Run Manifest Contract

**Status:** dependency-aware runner implemented; synthetic end-to-end fixtures/regression tests are the next block.

## Purpose

Execute the College + Career recommendation pipeline reproducibly without hard-coding the workflow into one monolithic script. Each stage remains independently testable; a stage manifest declares execution order through dependencies.

## Stage manifest

Required columns:

- `stage_id`
- `command`
- `depends_on` — semicolon-separated stage IDs
- `required`
- `inputs` — semicolon-separated paths
- `outputs` — semicolon-separated paths

Commands may use `{python}` and `{run_dir}` placeholders.

The manifest is policy/configuration and should be versioned with the code used for a run.

## Dependency behavior

A stage runs only after all dependencies have completed. If a prerequisite does not pass, dependent stages are marked `BLOCKED_BY_DEPENDENCY` rather than attempting to operate on incomplete artifacts.

Unknown dependencies and dependency cycles are hard errors.

## Required vs optional stages

Required-stage failure blocks the pipeline. Optional-stage failure is retained as `OPTIONAL_FAIL` and may allow later stages to continue when their declared dependencies permit it.

This is execution semantics only. Whether an optional limitation is acceptable for a recommendation release is governed separately by the release-gate manifest.

## Provenance

For each executed stage, the run manifest records:

- stage ID and dependencies;
- resolved command;
- required/optional status;
- return code;
- elapsed time;
- SHA-256 hashes of declared inputs;
- SHA-256 hashes of produced outputs;
- missing expected outputs;
- bounded stdout/stderr tails for diagnosis.

The stage-manifest SHA-256 is also recorded.

## Pipeline status

The runner emits:

- `PIPELINE_COMPLETED` when every required configured stage executed successfully;
- `BLOCKED` when any required stage failed or could not run.

`PIPELINE_COMPLETED` is **not** recommendation-release authorization. The separate release gate must inspect the resulting QA artifacts.

## Security / execution boundary

The stage manifest contains executable commands and must therefore be treated as trusted project configuration. It should not be populated directly from untrusted user/web input. Production deployment should execute only reviewed/versioned manifests in a constrained environment.

## Output

`recommendation_pipeline_run_manifest.json`

This becomes the run-level provenance record connecting code/configuration with the artifacts later inspected by the release gate.

## Intended dependency chain

The eventual complete manifest should connect, as applicable:

source/identity QA → candidate universe → feature assembly → career pathway evidence/alignment/optionality → feature registry → pre-score audit → normalization → dimension composition → weight scenarios → sensitivity → coverage/fairness → explanations → explanation QA → release gate.

Source ingestion jobs can remain separate upstream pipelines where appropriate; their immutable snapshots and QA artifacts become declared inputs.

## Next implementation block

Create **small synthetic fixtures plus an executable regression smoke test** covering both expected-pass and expected-block cases. The fixtures should be obviously synthetic and should test the architecture rather than mimic confidential institutional records. At minimum test:

- explicit hard-constraint exclusion;
- unknown evidence retained unless explicit policy excludes it;
- missing values not converted to zero;
- partial dimension composition blocked unless explicitly permitted;
- unspecified dimensions receive no preference weight;
- many-to-many career pathways remain visible;
- release gate blocks a missing/failed required QA artifact;
- pipeline dependency failure prevents downstream execution.
