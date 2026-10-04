# Interactive Match Service Contract

**Status:** v1 request/response boundary defined; implementation adapter next.

## Purpose

This contract turns the existing data and recommendation components into a stable boundary for a future web interface. The UI collects understandable choices; the service validates and translates them into governed constraints/preferences; domain components calculate evidence and matching; the service returns structured results that the browser renders without reinterpreting model semantics.

## Versioned schemas

- `schemas/match_request.schema.json`
- `schemas/match_response.schema.json`

Breaking semantic changes require a schema-version change. Data and model versions are separate from API schema version.

## Request principles

The request represents what the user actually supplied. Skipped questions are omitted rather than assigned neutral-looking invented values. Hard constraints and preferences are separate. Each hard constraint declares how unknown evidence should behave. Only explicit priorities enter preference weighting. Career preferences retain their declared alignment semantics. Geography distinguishes school location from intended work market. Transfer context is optional and does not imply transferability before authoritative evidence is evaluated.

The UI should generate stable `source_question_id` values so usability testing can trace how a plain-language question maps to a governed field without storing unnecessary free-text personal information.

## Response principles

A response is a shortlist/decision-support payload, not a claim that the first item is objectively the best college. Every returned candidate is institution × program identity. Eligibility is separate from fit. Dimension values are accompanied by coverage/evidence state. Explanations carry stable reason codes and evidence identifiers. Career pathways, transfer evidence, current local labor evidence, and long-term outlook remain separate structures. Source freshness is inspectable.

The browser must not convert missing evidence to zero, calculate a new score, infer transfer guarantees, infer admission probabilities, or merge current labor-market conditions with long-term projections.

## User-friendly translation layer

The eventual questionnaire should not expose schema terminology such as `operator`, `CIP`, `SOC`, `UNITID`, normalization, or evidence-state codes unless the user opens an advanced/source view. Examples:

- “I need an online option” can become a hard modality constraint.
- “Keep tuition/cost as low as possible” can activate an affordability preference.
- “I can’t spend more than $X” can become an explicit cost ceiling, with the interface clarifying which cost concept is being constrained.
- “I want work with a lot of analysis/problem solving” can become an explicit career-attribute preference using a governed O*NET mapping.
- “I’m transferring from CUNY” can activate transfer context without promising that any specific credit applies.
- “I want to work near home after graduation” can select home-local intended-work-market semantics independently from school-location constraints.

Question-to-schema mappings should live in a governed UI-definition artifact rather than hard-coded independently in each frontend component.

## Service operations

### `POST /match`
Accepts a v1 match request. Validates schema and supported fields, selects the requested or active approved data/model version, builds the candidate universe, assembles governed evidence, evaluates explicit preferences, applies release-approved recommendation logic, builds explanations, and returns a v1 match response.

### `POST /compare`
Uses stable candidate IDs and the same active data/model versions to return side-by-side semantic comparison rows. Comparison does not require re-ranking.

### `GET /candidate/{id}`
Returns candidate detail, evidence lineage, program/career pathways, transfer evidence where relevant, and source freshness.

### `GET /options`
Returns valid interface choices from the active snapshot: credential levels, institution/program fields, states/regions, modalities where supported, governed preference questions, and other controlled options. The frontend should not maintain a conflicting independent taxonomy.

### `GET /metadata`
Returns active schema/data/model versions, build/release timestamps, and source-vintage summary.

## Determinism

Given the same validated request, data version, model version, and service version, matching should be reproducible. The response should expose enough version information to reproduce or audit a result without exposing internal filesystem paths.

## Validation boundary

Malformed requests fail before domain execution. Unsupported constraint fields/operators fail rather than being ignored. User values are data, never executable command fragments. Service code calls Python/domain functions or controlled adapters; it does not construct shell commands from request values.

## Privacy

Anonymous matching should be possible. The matching request should contain decision-relevant choices, not identity by default. Free-text collection should be minimized. Demographic/audit data must not silently enter recommendation features.

## Initial UI flow supported by v1

1. Choose decision mode.
2. Add must-haves.
3. Add or skip optional priorities.
4. Add career/work preferences if useful.
5. Clarify school-location versus intended-work-market geography when relevant.
6. Add transfer context when relevant.
7. Receive shortlist with reasons, tradeoffs, unknowns, coverage, career pathways, and freshness.
8. Pin/compare candidates.
9. Revise a preference or constraint and rerun deterministically.

## Next implementation block

Build a pure-Python service adapter that validates/normalizes a request, maps it into the existing candidate/preference components, and assembles a schema-conformant synthetic response. Add deterministic fixtures for broad exploration, career-first, transfer, college/program-first, and returning-student paths before choosing a web framework.
