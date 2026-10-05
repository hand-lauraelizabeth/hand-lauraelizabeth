# Affordability & Outcomes Product Contract

Affordability and outcomes evidence must retain its source concept and grain. The matcher must not flatten every monetary field into “cost” or every earnings/completion field into a generic institutional quality signal.

## Distinct affordability concepts

At minimum, the product model keeps these concepts distinct when available: in-state tuition, out-of-state tuition, cost of attendance, net price, and debt. A user-entered “maximum cost” cannot be applied until the interface identifies which cost concept the constraint refers to. A preference to “keep costs low” may use a governed affordability dimension, but the component measures and normalization policy must remain inspectable.

Net price is not sticker price. Tuition is not total cost of attendance. Debt is an outcome of financing and attendance, not a price. Missing or suppressed values remain missing/suppressed and are never converted to zero.

## Outcomes grain

Institution-level completion, debt, or earnings evidence describes the institution-level population defined by its source. It must not be presented as the outcome of a particular program.

Field-of-study evidence remains field-of-study evidence. `affordability_outcomes_product_adapter.py` attaches field evidence to a product program only on an exact governed `(UNITID, CIP, credential level)` identity. It does not use program-title similarity to manufacture a match.

Where a source's field-of-study grain is broader than the local program inventory, multiple institution programs may legitimately reference the same field-level evidence. The interface/explanation layer should label the evidence as field-of-study rather than implying a program-specific cohort when the source does not support that claim.

## Product snapshot integration

Institution-grain affordability/outcomes can feed the existing institution-level `finance` enrichment of `product_snapshot_builder.py`. Field-of-study enrichment should remain separately namespaced at program grain; it should not be collapsed into the institution finance table.

A subsequent snapshot revision should therefore accept a dedicated program-outcomes enrichment family or a generalized governed enrichment manifest rather than forcing field outcomes through the current `finance` slot.

## Source lineage

Production extracts should carry source vintage and, where available, source record identifiers. The product manifest must propagate the relevant Scorecard/IPEDS vintages. Release QA should report coverage separately for each material concept instead of treating “has any finance data” as complete affordability coverage.

## Recommendation semantics

Completion and earnings are contextual outcome evidence, not guaranteed future outcomes. Debt and net price depend on populations and definitions that must remain visible. No source measure is a probability that a particular user will graduate, earn a particular salary, incur a particular debt, or receive a particular net price.
