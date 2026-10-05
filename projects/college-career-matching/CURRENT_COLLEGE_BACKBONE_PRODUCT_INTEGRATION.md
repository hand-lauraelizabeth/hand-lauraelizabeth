# Current College Backbone → Product Snapshot Integration

This layer connects authoritative/current institution and program extracts to the interactive product contract without allowing the UI or recommendation service to invent identities.

## Institution/program backbone

`current_college_backbone_adapter.py` accepts separately governed institution- and program-grain extracts. Production inputs should be the current IPEDS-derived backbone (or a governed equivalent) rather than a historical workbook.

Institution identity is exact `UNITID`. Program identity is exact `(UNITID, program_id)`. The adapter does not infer program IDs, CIP codes, institutions, or campus relationships from names. A program whose UNITID is absent from the institution universe is placed in the QA unresolved set and is not silently attached to a similar institution.

The normalized base is deliberately narrow: institution/program identity, CIP, credential level, state/city, and optional governed modality evidence. Other source families remain enrichments so their grains and missingness semantics stay visible.

## Accreditation evidence

`accreditation_product_adapter.py` reduces authoritative accreditation/DAPIP-style evidence to institution grain for product enrichment. Multiple agency/status records remain represented as evidence rather than being converted into an invented quality score.

Absence from the accreditation enrichment is **unknown coverage**, not evidence that an institution is unaccredited. Any future eligibility rule involving accreditation must use a specifically governed status interpretation based on the authoritative source semantics and applicable date, not `coverage__accreditation` alone.

## Vintage propagation

The backbone QA artifact records separate institution and program vintages. The accreditation QA artifact records its source vintage. During production orchestration, these values should be copied into `institution_program_product_snapshot_manifest.json -> source_vintages` so the activation gate can require the expected source families and the result interface can expose freshness.

## Coverage baselines

The first authoritative full run should establish—not assume—the following baselines: institution count, institution×program count, unresolved program identities, CIP completeness, credential completeness, state coverage, accreditation-evidence institution count, and accreditation coverage across product candidates. Those observed values can then support defensible regression thresholds in the snapshot release policy.

## Remaining authoritative connections

After the backbone/accreditation run, connect approved Scorecard/IPEDS affordability/outcomes fields at their defensible grains, then the existing transfer and career-pathway outputs. CUNY program/CIP coverage and the full institution-local labor-market run remain explicit current-data backlog items; neither should be disguised by fallback or inferred values.
