# NYC 311 Public Service Operations Explorer — review release candidate (2026-11-02)

**REVIEW RELEASE CANDIDATE — NOT A NEW PRODUCTION DEPLOYMENT.** The hosted review page was independently opened past the preview provider's consent notice and exercised in Chromium. The existing live WordPress page is separate and unchanged.

## Functional review preview

[Open review candidate](https://raw.githack.com/hand-lauraelizabeth/hand-lauraelizabeth/release/nyc311-interactive-preview-20261102/projects/nyc311-operations-intelligence/interactive-preview.html) — on the third-party host, select **Open the page** if an External Content Notice appears.

- Borough, complaint-type and 7/30-day filters, aggregate KPIs, accessible charts/table, CSV export, borough complaint-composition ratios.
- ZIP-grouped noise and housing complaint comparison with category and 7/30-day controls, minimum 20 requests, 5,000-group response cap, and stale-result invalidation. This is a ZIP ranking, not a polygon map or population-normalized incident rate.
- Offline fictional example: 160 explicitly invented requests; visibly labeled **FICTIONAL EXAMPLE / NOT NYC Open Data**. No raw individual requests, addresses or coordinates embedded.
- API failures show unavailable state and em-dash KPIs, not fabricated zero totals; stale responses cannot replace fictional mode.

## Independent evidence (Nov 2, 2026 ET)

- Hosted/mobile browser smoke **SUCCESS**: [GitHub Actions run 41556396354](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/41556396354), tested code/workflow head `1f14ca68521eef7ed252cabd66cf0d10319ad276`.
- Exact job log: hosted consent notice traversed; actual application heading rendered; mocked source gave 140 displayed requests; Queens filter 100; fictional mode 160; ZIP count 9 suppressed, count 44 retained; changing complaint family cleared stale results. axe-core WCAG 2/2.1 A/AA scan found **zero serious or critical violations** at a 390px viewport; no JS page errors. This is not a complete manual accessibility audit.
- Local deterministic Playwright smoke **PASS** in same run: filters, source-failure blank KPIs, 30-day ZIP bounds, suppression, reset, refresh, empty states.
- **Separate existing production WordPress page** live-source smoke **PASS** in same run: 55,058 displayed grouped requests; Queens 12,449; 357 displayed categories at test time. These are mutable observations, not citywide reconciled counts. This validates the existing live page, **not** the new review candidate's unmocked API query.
- Source: [NYC Open Data 311](https://data.cityofnewyork.us/d/erm2-nwe9), Socrata dataset `erm2-nwe9`. Hosted test deliberately mocks API responses for deterministic verification; review candidate's live query still needs direct independent source validation.

## Remaining before production

1. Independently exercise **review candidate's own unmocked live API** across 7/30-day windows, including partial-response and throttling behavior; do not infer official totals.
2. Broader keyboard/screen-reader/mobile and disclosure-differencing review, including temporal cross-table inference.
3. Obtain fresh explicit approval before merging or updating WordPress. No unapproved private September request-level data, source CSV, or new WordPress publication.

The separate historical September unique-key CSV reconciliation and privacy-sensitive cross-table audit remain HOLD. The existing live WordPress deployment is not evidence that those research-grade checks are complete.
