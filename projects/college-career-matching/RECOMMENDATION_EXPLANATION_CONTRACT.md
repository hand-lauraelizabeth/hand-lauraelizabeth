# Recommendation Explanation Contract

**Status:** structured explanation-evidence builder implemented; audience-facing renderer and empirical explanation QA pending.

## Principle

Explanations are part of the recommendation model, not marketing copy added after ranking. Every material statement shown to a user must trace to an observed field, declared rule, source lineage, and evidence state.

The design follows four useful explainability properties articulated by NIST: provide reasons/evidence, make explanations meaningful to the intended user, ensure the explanation accurately reflects the process, and respect knowledge limits.

## Explanation record types

The canonical layer distinguishes:

- `reason`: evidence supporting fit with a stated preference
- `tradeoff`: evidence that may make the option less suitable under a stated preference
- `uncertainty`: missing, suppressed, unresolved, weak, or unstable evidence
- `condition`: qualification attached to a claim, especially transfer/admissions/program requirements
- `context`: useful evidence that should not be framed as inherently positive or negative
- `review`: a human-review state that prevents stronger claims

## Required traceability

Each reason code should retain or point to:

- candidate ID
- dimension
- source field
- observed value/evidence state
- source family
- source vintage/retrieval date
- specificity (institution/program/course/occupation/geography)
- declared rule that generated the explanation
- priority/display role

The explanation builder emits machine-readable evidence records. It deliberately does not ask a language model to infer why a candidate ranked highly.

## Claim-strength rules

1. Do not call a transfer outcome guaranteed unless the authoritative source explicitly supports that guarantee and applicable conditions are represented.
2. Do not turn admissions context into an individual admission probability without a validated probability model.
3. Do not state that a program leads to a specific occupation merely because a many-to-many CIP↔SOC crosswalk contains the pair; describe it as a pathway/link unless stronger evidence exists.
4. Do not treat local OEWS absence or suppression as poor labor demand.
5. Do not treat unresolved identity/CIP/equivalency as negative evidence.
6. Do not call small score/rank differences meaningful unless stability testing supports the distinction.
7. Do not imply the institution-local labor market is the user's intended work market unless the user selected it.
8. Separate current labor-market evidence from long-run projections.

## User-facing explanation structure

A mature recommendation card/detail view should be able to show, in this order:

1. **Why it matches** — strongest evidence tied to stated preferences.
2. **Tradeoffs to consider** — material countervailing evidence, not generic disclaimers.
3. **Transfer/pathway details** — only when relevant, with conditions and evidence specificity.
4. **Career/labor-market context** — pathways, projections, current local evidence, and geography assumptions kept distinct.
5. **What we don't know yet** — material uncertainty or source gaps.
6. **Stability** — whether the option remains strong across reasonable weighting scenarios.
7. **Sources** — source families/vintages behind material claims.

The default view should be concise; technical lineage can be expandable.

## Reason-code policy

Reason codes must be declarative and stable, e.g. `AFFORDABILITY_NET_PRICE_MATCH`, `PROGRAM_CIP_MATCH`, `TRANSFER_PROGRAM_REQUIREMENT_EVIDENCE`, `LOCAL_WAGE_EVIDENCE_PRESENT`, `UNRESOLVED_PROGRAM_CIP`, `RANK_WEIGHT_SENSITIVE`.

A policy row defines:

- `reason_code`
- `dimension`
- `field`
- `operator`
- `threshold`
- `explanation_type`
- `template`
- optional source/vintage/specificity/priority metadata

No default substantive thresholds are embedded in the builder. Thresholds belong in a versioned policy after empirical validation.

## Explanation QA gates

Before release, test:

- every displayed material claim maps to evidence
- reason code determinism/reproducibility
- no contradiction between reason and tradeoff records
- uncertainty shown when it could change interpretation
- source specificity correctly represented
- compound transfer rules preserved
- rank-stability language agrees with sensitivity output
- templates do not overstate causal or predictive meaning
- readable without color alone
- understandable in user testing
- expandable technical detail available for audit

## Knowledge-limit behavior

If evidence is insufficient for a claim, the correct explanation is the limitation—not a plausible-sounding substitute. A candidate can remain visible with partial evidence; the interface should distinguish limited evidence from poor fit.

## Next implementation block

Build the **recommendation explanation QA/renderer contract** that joins reason records to pre-score review states and sensitivity/stability results, blocks contradictory/unsupported claims, and emits a deterministic audience-facing explanation payload suitable for web/UI rendering. Only after that should the project begin calibrating candidate dimension normalization and baseline weights.
