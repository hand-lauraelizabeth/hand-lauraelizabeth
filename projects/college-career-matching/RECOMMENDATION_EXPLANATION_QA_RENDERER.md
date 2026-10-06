# Recommendation Explanation QA & Renderer Contract

**Status:** executable QA/renderer implemented; production UI integration pending.

## Purpose

Structured explanation evidence is only useful if the final presentation cannot silently overstate it. This layer sits between evidence/reason construction and the eventual website/application UI.

It performs two jobs:

1. validate that reason records are internally consistent and supported by evidence;
2. convert validated records into a deterministic machine-readable payload.

It does **not** generate persuasive free-form prose after seeing a rank.

## Inputs

### Structured reason records

Required fields:

- candidate ID
- `reason_code`
- `reason_kind`
- `dimension`
- `claim_text`
- `evidence_state`
- `source_family`
- `source_vintage`
- `specificity`

Supported reason kinds:

- `support`
- `tradeoff`
- `uncertainty`
- `condition`
- `context`
- `review`

Optional lineage such as source URL, evidence strength, and conditions is retained in the render payload when present.

### Review queue

The pre-score audit review queue may be joined so unresolved evidence blocks validated recommendation rendering rather than disappearing from the presentation layer.

### Stability results

The sensitivity harness output may be joined so users can see whether a result is robust across approved scenarios.

## Blocking QA rules

The initial executable gate blocks a candidate when:

1. a support/tradeoff claim is based on an evidence state that means the evidence is unknown, suppressed, not evaluated, unresolved, outside source coverage, or otherwise insufficient;
2. a material support/tradeoff/condition claim lacks source-family lineage;
3. the same reason code is simultaneously represented as both support and tradeoff for the same candidate/dimension;
4. the candidate has an open pre-score review trigger.

Blocked candidates retain their structured evidence for diagnosis. They should not be displayed as validated recommendations.

## Render payload

Each candidate payload contains stable sections:

- `why_it_matches`
- `tradeoffs`
- `conditions`
- `what_we_dont_know`
- `context`
- `review_notes`
- `stability`
- QA/render status

The UI may change labels or visual presentation, but it should not change the semantic category of a reason without updating the underlying reason record.

## Claim-strength rules

The renderer inherits the upstream explanation contract. In particular:

- course equivalency is not automatically major applicability;
- transfer-path evidence is not automatically guaranteed admission;
- CIP↔SOC is a pathway relationship, not proof of an individual career outcome;
- missing/suppressed OEWS data is not weak demand;
- local labor-market evidence describes a geography, not a student's guaranteed destination market;
- earnings/outcome evidence should retain population/cohort context;
- score/rank differences are not probabilities;
- unstable recommendations require stability context rather than stronger prose.

## Explainability rationale

The design follows a useful separation between **evidence/reasons**, **meaningful presentation**, **accuracy to the actual recommendation process**, and **knowledge limits**. The renderer therefore cannot substitute rhetorical confidence for missing evidence.

## Current interactive trace integration

The public matcher now implements the source-detail interaction pattern for the narrow career/labor-priority explanation subset: each service-supplied context or uncertainty record can expose its structured supporting evidence through a keyboard-native `details/summary` disclosure. This integration does not replace the broader QA renderer or claim-validation gate; it demonstrates the intended source/vintage drilldown behavior on a bounded, deterministic explanation family.

## Accessibility requirements for UI integration

The eventual interface should render the payload so that:

- semantic section headings are exposed to assistive technology;
- uncertainty and QA state are text, not color alone;
- reason lists and source details are keyboard accessible;
- source/vintage detail can be expanded without hiding the concise explanation;
- mobile ordering preserves the semantic hierarchy;
- icons never carry unique meaning without text labels.

## Outputs

- `recommendation_explanation_qa.csv`
- `recommendation_explanation_payload.json`
- `recommendation_explanation_qa_summary.json`

## Next implementation block

Build the **recommendation candidate-set and dimension-normalization contract**. The validation architecture is now sufficiently defined that the next modeling step should specify exactly what constitutes one candidate (institution, institution+program, and transfer-path variants), how each recommendation dimension is normalized without converting missingness into disadvantage, and which dimensions are user constraints versus scored preferences. Production weights remain gated until that layer is explicit and empirically tested.
