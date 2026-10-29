# Grant Budget & Evidence Ledger

A free, browser-local review tool for comparing a grant's planned budget with user-entered expenditure allocations. It does not determine whether a cost is allowable, allocable, reimbursable, or compliant.

## Use

Open the page from a static web server. Replace the fictional sample award, enter its dates, and add budget categories. Enter transactions with unique transaction IDs, exact source IDs, dates, amounts, assigned percentages, allocation bases, and supporting-document references. Use **Edit** on an expenditure to correct its source, date, category, amount, allocation, basis, reference, or note without changing its transaction ID. Save recalculates totals and review flags; an invalid edit does not change saved evidence, and Cancel discards edits. Compare planned versus assigned amounts, review flags, and download CSV or JSON. No account, financial connection, or upload is required.

The interface stores records only in the current tab. Export before refreshing or closing. Choose **Current-state JSON (no correction history)** to export only the latest saved award, budget, transactions and review flags, without previous correction values. Choose **Evidence JSON (with correction history)** to include earlier values. Both downloads contain current user-entered identifiers, notes and evidence references, so keep them private. **Evidence JSON with correction history includes:** each successful changed edit records its sequence number and exact before/after input values, including source IDs. Invalid, canceled and unchanged edits do not create entries. The history is limited to 500 corrections; download Evidence JSON before reaching the limit. This is a user-entered change log, **not an independently authenticated audit trail**. Award and category edits are not tracked. The history-bearing JSON may contain earlier sensitive values. Current-state JSON does not contain the correction-history field or prior values that exist only in the history. CSV represents only the latest saved records; its spreadsheet-formula precaution changes some values and is not universally reliable after spreadsheet re-save.

All money calculations use integer cents. Partial allocations use the user-entered percentage, rounded to the nearest cent; the residual is shown as unassigned. Missing allocation bases, missing evidence references, dates outside the award period, and budgets exceeded are **review flags**, not accounting conclusions. Source IDs are preserved exactly. Multiple transactions may cite the same source document.

This is a single-award review prototype; it does not enforce award restrictions, assess indirect cost rates, calculate cost sharing, or establish grant eligibility.

## Public sources

Official U.S. eCFR, accessed October 13, 2026: [2 CFR 200.302](https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200/section-200.302) (financial records and budget comparison), [200.403](https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200/section-200.403) (cost allowability factors), and [200.405](https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200/section-200.405) (allocable costs). Requirements differ by award and funder.

Accessibility design references [WCAG 2.2](https://www.w3.org/TR/WCAG22/). CSV precautions follow [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection).

## Testing

Run `node core.test.mjs` and `node correction-history.test.mjs` for committed synthetic calculation, revision-integrity and history-omission tests. Manual screen-reader, Firefox/WebKit, 200% browser zoom, deployed Content Security Policy, and native spreadsheet reopening checks remain outstanding. Do not publish as a production tool before review.
