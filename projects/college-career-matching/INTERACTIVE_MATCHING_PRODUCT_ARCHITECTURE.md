# Interactive College + Career Matching Product Architecture

**Status:** implementation roadmap connecting the current-data/recommendation engine to a user-facing matching product.

## Product objective

The eventual tool should let a person move from goals and constraints to a manageable set of college-program-career pathways, understand why each result appears, change assumptions, compare alternatives, and inspect evidence without needing to understand the underlying federal/state data architecture.

The interactive product is therefore not a dashboard placed on top of a ranking table. It is a stateful decision-support workflow built around the existing candidate, evidence, constraint, preference, validation, and explanation contracts.

## Public interaction principle

The primary public experience must be a normal browser page that is useful immediately on arrival. It must not require a local environment, notebook, terminal, download, account, sign-in, or a separate "run" action before a visitor can begin.

- Show meaningful results or examples on first render.
- Expose a small set of understandable preference controls immediately; update results in place as choices change.
- Treat longer questionnaires, advanced weighting, comparison, and source inspection as optional progressive disclosure rather than prerequisites.
- Prefer progressive enhancement: the page should retain readable explanatory/example content if JavaScript is unavailable, while JavaScript adds filtering, reordering, comparison, and richer explanations.
- Keep hard constraints visually distinct from softer priorities, but do not force visitors through a multi-step wizard to reach results.
- Preserve anonymous basic use. Persistence/accounts remain optional future capabilities.
- A public demonstration must use clearly fictional or validated public data and must not imply that review-eligible model artifacts are production-authorized.

## End-to-end product flow

### 1. Start with the user's decision

The entry flow should establish whether the user is primarily:

- exploring careers and wants programs/colleges that support them;
- exploring colleges/programs and wants to understand career pathways;
- comparing known colleges/programs;
- planning transfer;
- returning to school with existing credits/constraints;
- exploring broadly without a fixed career or major.

The tool must not require a declared occupation or major to begin.

### 2. Collect hard constraints separately from preferences

Hard constraints should be visually and semantically distinct from preferences. Examples include credential level, required program/field, geography, modality, explicit cost ceiling, transfer requirement, and programmatic accreditation/licensure requirements where applicable.

Unknown evidence should remain visible unless the user explicitly chooses a conservative exclude-unknown policy.

### 3. Build preferences progressively

Do not begin with a long technical questionnaire. Use progressive disclosure and plain-language prompts. Users may skip preferences. Only explicit preferences enter weighting/alignment.

Preference families should include:

- affordability and financing priorities;
- academic/program interests;
- institution/environment preferences;
- transfer/pathway priorities;
- geography and intended work market;
- career interests/work characteristics;
- labor-market priorities such as current local demand or long-term outlook.

The UI should translate plain-language choices into the governed profile/operator schema; it should never ask users to select mathematical operators directly.

### 4. Generate the candidate universe

The backend candidate grain remains institution × program, with pathway variants only where a transfer route materially changes conditions or degree progress.

The interactive layer sends explicit constraints to the candidate-universe engine and receives eligible, eligible-with-unknown, review, and excluded states. Exclusion reasons should be inspectable.

### 5. Assemble and normalize evidence

Candidate evidence is assembled from versioned current-data snapshots. Normalization uses declared reference populations and manifests, never the currently displayed result set.

The product must keep evidence coverage separate from desirability. Missing, suppressed, unresolved, and not-published states should render as uncertainty/coverage information rather than zeros.

### 6. Produce recommendation scenarios

The initial interactive experience should emphasize a shortlist and tradeoffs rather than a single authoritative rank. Where a composite ordering is eventually validated, the interface should still expose dimension-level fit and sensitivity.

Users should be able to change a preference or constraint and see which results change and why. The backend should support deterministic re-runs from the same data/model/profile versions.

### 7. Explain each result

Every result card should be backed by the structured explanation layer and show, in user-facing language:

- why it matches;
- important tradeoffs;
- affordability evidence;
- program/academic fit;
- transfer/pathway conditions when relevant;
- related career pathways and career-preference alignment;
- current labor-market evidence and long-term outlook as separate concepts;
- important unknowns/coverage limitations;
- source freshness.

Small score differences must not be presented as meaningful precision unless validation supports that interpretation.

### 8. Compare candidates

Users should be able to pin candidates and compare them side by side. Comparison should use stable semantic rows rather than forcing every field into a numeric score. Missing evidence should remain visibly missing.

Suggested comparison groups: cost/aid, program, completion/context, transfer, career pathways, local labor market, long-term outlook, preferences, evidence coverage.

## Updated-college-data contract

The interactive product should never query arbitrary live source pages during a user session. It should read from validated, versioned snapshots produced by the ingestion pipeline.

A publishable data build should include:

1. institution identity and current operating/status coverage;
2. current program inventory and CIP identity;
3. College Scorecard consumer/outcome fields where available;
4. IPEDS institution/program backbone;
5. DAPIP/accreditation evidence;
6. authoritative transfer/articulation evidence for implemented systems;
7. CIP↔SOC pathway crosswalk;
8. O*NET career characteristics;
9. BLS current OEWS and long-term projections;
10. local labor-market geography joins;
11. source vintage, retrieval timestamp, hashes, QA, and coverage artifacts.

Data refresh and product deployment should be separable: a new snapshot is promoted only after regression/coverage/release gates pass.

## Service boundary

The existing scripts should remain testable domain components. The interactive application should call a thin service/orchestration layer rather than execute arbitrary shell commands from user input.

Recommended service operations:

- `GET /metadata` — active data/model versions and source freshness;
- `GET /options` — valid UI choices derived from governed data, such as credential levels, states, modalities, fields, and preference definitions;
- `POST /match` — validated profile/constraint payload → recommendation result set;
- `POST /compare` — selected candidate IDs → comparison payload;
- `POST /explain` or embedded explanation payload — structured evidence for selected candidates;
- `POST /sensitivity` — controlled preference-change scenarios;
- `GET /candidate/{id}` — candidate detail and evidence lineage.

These are logical contracts, not a mandated web framework.

## Session/profile schema

A user session should preserve:

- explicit hard constraints;
- explicit preferences and importance;
- skipped/unspecified questions;
- geography semantics (school location, home, intended work market, remote/national);
- transfer context if applicable;
- pinned/comparison candidates;
- active data/model versions.

The tool should support anonymous sessions for basic use. Persistent accounts are a later product decision, not a prerequisite for matching.

## Response payload requirements

A match response should contain enough structure for a web UI without recomputing model semantics in the browser:

- candidate ID, institution/program identity and display labels;
- eligibility/disposition;
- dimension values and evidence states;
- preference/scenario information used;
- explanation sections;
- career pathway summaries and representative pathways;
- transfer evidence where applicable;
- current/local and long-term labor evidence kept separate;
- evidence coverage and review flags;
- source/data/model version identifiers;
- stable reason codes for UI rendering and analytics.

The browser should format and interact with these fields; it should not independently reinterpret missingness, calculate recommendation scores, or infer transfer guarantees.

## Accessibility and usability requirements

The product should be keyboard operable, screen-reader navigable, responsive on mobile, and usable without color distinctions. Results should have semantic headings and tables, visible focus states, sufficient contrast, plain-language uncertainty, and text equivalents for charts. Sliders should always have keyboard controls and displayed numeric/text values.

Progressive disclosure should keep the initial flow manageable while allowing advanced users to inspect assumptions, evidence, and source lineage.

## Privacy boundary

Do not require sensitive personal data for matching unless a later feature has a documented need and governance plan. Demographic information used for model auditing should not silently become a recommendation feature. User-entered profile data and analytical QA datasets should remain conceptually and operationally separate.

## Analytics for product improvement

If usage analytics are added, prefer event-level product telemetry such as question skipped, filter changed, result pinned, comparison opened, explanation expanded, and preference changed. Do not treat clicks as proof that a recommendation was good. Evaluation should combine usability research, coverage/error review, stability tests, and outcome research where legitimately available.

## Implementation sequence

### Phase A — data-ready backend

Complete authoritative current college/program snapshots, remaining transfer/program identity coverage, local labor joins, source/version manifests, and release gates.

### Phase B — recommendation API contract

Create typed request/response schemas around the existing candidate, preference, dimension, career, explanation, and QA outputs. Add deterministic fixture tests at the service boundary.

### Phase C — interactive prototype

Build the smallest usable flow: decision entry → hard constraints → optional preferences → shortlist → result explanation → compare → revise preferences. Use synthetic or validated public data snapshots only.

### Phase D — usability/accessibility validation

Test comprehension of hard constraints versus preferences, missing evidence, transfer conditions, career-pathway language, labor-market geography, comparison, and sensitivity. Conduct keyboard/screen-reader/mobile QA.

### Phase E — calibrated recommendation release

Only after data coverage, sensitivity, fairness/coverage, explanation, accessibility, and manual end-to-end gates pass should the product move from exploratory matching to a validated recommendation release.

## Immediate engineering backlog

1. Keep current-data ingestion and coverage work ahead of visual polish.
2. Harden the pipeline runner so user/session input can never reach shell execution.
3. Define versioned request/response schemas for `/match`, `/compare`, and candidate detail.
4. Build a deterministic recommendation-service adapter over the existing modules.
5. Create synthetic end-to-end service fixtures representing first-time, transfer, career-first, college-first, and broad-exploration users.
6. Add product-level accessibility and explanation QA fixtures.
7. Prototype the interaction only after the service boundary can return stable synthetic results.

Power BI work can complement analysis, validation, and portfolio demonstration, but the interactive matching product should not depend on Power BI availability or licensing.