# Workforce Opportunity & Skills Intelligence Explorer — review candidate

Status as of 2026-11-02 17 ET: **REVIEW PREVIEW, NOT YET A VERIFIED RELEASE CANDIDATE**.

## Functional preview
Open `interactive-preview.html` in a local browser. It works offline with **explicitly fictional** occupational records. Available interactions: area, occupational group, occupation/SOC search, annual median wage threshold, sorting, wage bar chart, accessible table, estimate coverage, reset, CSV export, reviewed-schema CSV import, clear/restore, and informative empty state. No private data, source-level respondent data, or raw person-level records.

## Evidence and data limitations
- Official reference: [BLS OEWS May 2025 tables](https://www.bls.gov/oes/tables.htm); May 2025 estimates released **May 15, 2026**. This prototype does **not** embed real OEWS data. Fictional names and numbers must never be presented as BLS estimates.
- Imported CSV must have `area,occupation,soc,group,employment,annual_median_wage`; no inferred provenance. Source must be reviewed for vintage, geography, SOC, suppression, unit conventions, duplicate records and row coverage.
- Missing/suppressed numeric cells remain blank/unavailable, not zero. BLS employment estimates are **not** job openings, growth rates, or projected vacancies. Wages are not starting salaries. Geographic areas may overlap.
- No CIP–SOC crosswalk, educational program availability, admissions requirements, credential, or licensure inference. ACS PUMS integration is deferred pending survey weights, geography and uncertainty validation.

## Independent tests and release gates
- `node projects/workforce-opportunity-explorer/test_interactive_preview.cjs` after installing `playwright@1.56.1` and `axe-core@4.10.3` and Chromium. Tests: fictional disclosure, area/group/search filters, empty state, reset, import, missing employment, wage floor, duplicate rejection, clear/restore, axe WCAG 2.0/2.1 A/AA serious/critical, no JavaScript page errors.
- CI: `.github/workflows/workforce-interactive-preview.yml`; **result pending verification** at this document's creation.
- Required for release-candidate designation: passing exact-commit independent browser and accessibility CI, functional hosted preview URL tested by a separate browser, and readback-verified backlog status.
- No production WordPress publication or merge without separate approval.

## Review
Branch: `release/workforce-interactive-preview-20261102`.
Consolidated draft PR: https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/pull/458.
