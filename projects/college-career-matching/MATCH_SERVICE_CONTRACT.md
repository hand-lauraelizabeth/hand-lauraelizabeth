# Interactive Match Service Contract

**Status:** v1 request/response boundary implemented and exercised with synthetic contract fixtures.

## Purpose

The service is the semantic boundary between the governed College + Career data/model layers and an interactive interface. The browser collects understandable choices and renders service responses; it does not independently calculate recommendation semantics.

## Versioning and determinism

`schema_version` versions the API contract. `data_version` and `model_version` identify the evidence/model inputs independently. For the same validated request plus data/model versions, `request_id` is deterministic. `generated_at_utc` records response generation time and is not part of the deterministic identity.

## Request semantics

Hard constraints and preferences are separate. Constraint fields/operators must exist in the governed constraint registry. Skipped preferences do not receive invented weights. Unknown evidence follows the constraint's explicit `unknown_policy`.

School geography and work geography are separate. `geography.work_market_semantics` describes the user's intended interpretation. When a specific labor market is selected, `geography.intended_work_market` carries explicit `market_id` and `market_type`; it is not inferred from school location.

Affordability constraints identify a governed measure concept. A net-price ceiling is not silently treated as tuition or cost of attendance.

## `POST /match`

The response contains institution × program candidates, eligibility, dimensions, explanations, career pathways, transfer evidence, labor evidence, evidence coverage, freshness, and pagination.

`result_count` is the total eligible result count before pagination. `pagination` reports page, page size, total pages, and previous/next availability. Page numbers begin at 1; v1 page size is 1–100.

Duplicate candidate IDs fail closed rather than producing ambiguous results.

## Career pathway evidence

Each match result carries a descriptive `career_pathways` block with a mapped pathway count, SOC codes, and structured related-pathway rows. A pathway row contains the governed SOC code and an occupation title only when that title is present in the upstream governed evidence; the service does not manufacture titles from names or browser lookups.

The full mapped pathway set is distinct from `representative_pathways`. The latter is reserved for reviewed career-preference alignment/explanation logic and may be empty. Pathway count is descriptive and is not, by itself, a quality score, placement probability, or graduate-outcome distribution.

## Labor evidence

`labor_market.selected_work_market` contains current evidence only for the explicitly selected market. If the selected market has no evidence, the state is `unavailable`; the service does not silently substitute school-local, state, or national current evidence.

`labor_market.long_term_outlook` is a separate evidence family. Long-term projections remain available when appropriate even when current selected-market evidence is unavailable. A projection is not presented as current hiring evidence.

## Evidence states

Affordability/outcomes evidence uses governed states including `observed`, `missing`, `suppressed`, `unresolved`, and `not_published`. Blank evidence without an authoritative source state is `missing`; suppression is never inferred. Numeric zero may be an observed value and is not equivalent to missing/suppressed evidence.

Institution-level outcomes are not presented as program outcomes. Tuition, cost of attendance, net price, debt, completion, and earnings remain distinct concepts.

## Other service operations

`GET /metadata` returns governed data/model version information, snapshot identity, source-vintage labels, and machine-readable release readiness. It does not convert review eligibility into production authorization and does not infer freshness from a vintage label. `GET /options` returns choices and constraint capabilities from the same product data version. `GET /candidate/{id}` returns evidence-oriented candidate detail. `POST /compare` returns 2–5 candidates side by side without declaring an automatic winner.

## Recommendation ranking boundary

The base match service remains an eligibility/evidence service and does not manufacture a ranking from available numeric fields. Baseline recommendation scores are created only by the explicit-priority materializer, sent through sensitivity/validation, and then passed through the recommendation release gate.

A browser or service response must not treat a calculated `ranked_pending_validation` row as review-eligible. Ranked metadata may be surfaced only from a gated, identity-bound ranking bundle derived from `review_eligible_ranked_candidates.csv` (or an equivalent artifact with the same gate decision). `ELIGIBLE_FOR_REVIEW` remains distinct from production authorization.

The ranking bundle binds the ordering to the decision semantics, `data_version`, `model_version`, and the complete eligible candidate universe. `page` and `page_size` are excluded from the ranking-context hash so the same validated ordering can be paginated; changing a constraint, priority, career preference, geography, data/model version, or eligible universe invalidates the bundle and fails closed. Pagination is applied only after the validated ranking order.

## Browser boundary

The browser may format, filter display state, collect answers, and request new service results. It must not convert missing evidence to zero, calculate its own recommendation score, infer transfer guarantees/admission probabilities, reinterpret measure concepts, or merge current labor evidence with long-term projections.

## Privacy

Anonymous matching should be possible. Requests should contain decision-relevant choices rather than identity by default. Free text should be minimized. Demographic/audit attributes must not silently become recommendation features.

## Current implementation path

- `schemas/match_request.schema.json`
- `schemas/match_response.schema.json`
- `schemas/metadata_response.schema.json`
- `metadata_service_adapter.py`
- `match_service_adapter.py`
- `constraint_field_registry.py`
- `measure_metadata_registry.py`
- `options_service_adapter.py`
- `candidate_detail_service.py`
- `compare_service_adapter.py`
- `prototype/service-client.js`

Synthetic fixtures remain explicitly non-production until an authoritative current product snapshot passes the release gate.
