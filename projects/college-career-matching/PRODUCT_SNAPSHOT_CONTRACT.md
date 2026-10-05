# Institution × Program Product Snapshot Contract

The interactive matcher and its `/options` endpoint must consume the same versioned product snapshot. This artifact is the boundary between source-specific ingestion/coverage work and the user-facing matching product.

## Grain and authority

One row is one institution × program candidate identified by `(UNITID, program_id)`. The base institution/program inventory defines the universe. Required base fields are `UNITID`, institution name, program ID/name, CIP code, credential level, and state. Enrichment sources may add evidence but may not silently add, remove, merge, or duplicate candidates.

## Enrichment families

The first product build supports separately governed joins for:

- accreditation/institution standing at institution grain;
- affordability/outcomes evidence at institution grain where that is the source's defensible grain;
- transfer/pathway evidence at institution × program grain;
- career-pathway evidence at institution × program grain.

Enrichment columns are namespaced (`accreditation__`, `finance__`, `transfer__`, `career__`) to prevent source families from overwriting base identity or each other.

## Missingness

Optional enrichment is left-joined. Missing accreditation, financial/outcomes, transfer, or career enrichment creates an explicit coverage state and never becomes zero, failure, poor quality, non-transferability, weak career prospects, or another negative recommendation signal.

## Versioning and provenance

Each build writes:

1. `institution_program_product_snapshot.csv`
2. `institution_program_product_snapshot_manifest.json`

The manifest records data version, build time, grain, candidate/institution counts, SHA-256 hashes of every supplied input, the SHA-256 of the generated snapshot itself, and enrichment coverage counts. The release gate recomputes the snapshot hash and blocks activation if the reviewed CSV is missing a valid manifest hash or does not match it.

## Current-data integration

The production base should come from the current authoritative institution/program build (IPEDS backbone plus governed identity/program layers). Accreditation should come from the approved accreditation/DAPIP layer. Affordability/outcomes should use approved College Scorecard/IPEDS fields with their actual grains preserved. Transfer and career joins should use the already-governed transfer and CIP→SOC/O*NET/BLS pipelines.

Source vintages must remain available in the joined evidence or accompanying lineage artifacts. Current OEWS evidence and long-term BLS projections remain distinct downstream even when both contribute to career evidence.

## Product rule

`interface_options_builder.py` should consume this snapshot for current selectable choices. Matching should consume this same snapshot/version for its candidate universe. This prevents a user from selecting a college/program that the active matcher cannot identify—or receiving a recommendation for an entity absent from the active interface universe.

## Release checks

Before activation, QA verifies base identity uniqueness, non-empty required fields, candidate-count regression floors, configured enrichment-coverage thresholds, source vintages, input hashes, exact snapshot-output hash identity, manifest counts/versioning, and successful interface-options generation. Thresholds remain policy-configured rather than invented in code. Enrichment join cardinality and orphan identities are enforced during snapshot assembly, so invalid enrichment cannot reach the activation gate as a silently altered candidate universe.
