# NYC 311 Public Service Operations Explorer — candidate status (2026-11-02)

**Review branch only. NOT a verified release candidate or production publication.**

## Functional review-branch capabilities
- Borough, complaint-type, and 7/30-day filters; KPI summary, accessible aggregate charts/table, CSV export and concentration comparison.
- ZIP-level grouped noise and housing comparison with category and 7/30-day filters, server-side complaint-family filtering, 20-request minimum, and bounded 5,000-group fail-closed guard.
- Explicit **Try fictional example (offline)** button populates 160 invented aggregate requests (two boroughs, two categories, two statuses) without a network call; the source label and live region explicitly say FICTIONAL EXAMPLE / NOT NYC Open Data. Live refresh returns to the real source.
- Main aggregate no longer sends a `$having` clause; small-group filtering remains in the client. API failure blanks summary metrics instead of falsely displaying zero; stale responses cannot replace a synthetic view.

## Test evidence and commands
- GitHub readback verified HTML and Playwright source, V8 JS syntax parse and source-contract checks on Nov 2. This **is not a browser/CI pass**.
- Independent test: `node projects/nyc311-operations-intelligence/test_interactive_preview.cjs` (requires Playwright/Chromium); exercises mocked API, filters, synthetic mode, source provenance, HTTP503 recovery, ZIP small-cell suppression, 30-day bounds.
- Workflow: `.github/workflows/nyc311-interactive-preview.yml`; exact-head workflow lookup returned no runs at writing. Browser execution and accessibility automation remain unverified.
- Source: https://data.cityofnewyork.us/d/erm2-nwe9 ; API: https://data.cityofnewyork.us/resource/erm2-nwe9.json . The ZIP-level chart is a ranked comparison, **not a polygon map**.

## Release blockers
1. Independent Playwright execution and automated accessibility audit on exact head, with passing logs.
2. Real NYC 311 API query validation (no invented live counts) and documented handling of query limit and source changes.
3. A working hosted HTML preview URL with demonstrated keyboard/filter interactions and no exposed request-level data.
4. Release sign-off. **No production WordPress update, merge, or publication without explicit approval.**

## Privacy and interpretation
Aggregates only; no addresses or individual request-level records. Suppressed groups mean displayed totals are **not official complete counts**. Administrative closure is not confirmed problem resolution. Repeated temporal releases and intersecting marginals may reveal small groups; do not treat this live aggregate prototype as approval to publish the private September CSV workflow.
