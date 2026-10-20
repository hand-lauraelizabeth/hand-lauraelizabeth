# Cash Flow & Bill Timing Simulator

A browser-local planning tool for dated income, bills, and end-of-day projections. Compare a shifted payment date against the original baseline and export the scenario as CSV. No account, bank connection, or remote upload is required.

Use a local static HTTP server to serve this directory; JavaScript modules do not work reliably from file URLs. Run `node engine.test.mjs` for deterministic regression checks.

Amounts use integer cents. Monthly dates are clamped to the last calendar day when needed. The tool does not model settlement times, overdraft fees, or bank rules, and cannot provide financial determinations. CSV export adds apostrophes to suspicious textual cells; that precaution can change text and is not a universal guarantee.

Reference: CFPB Your Money, Your Goals toolkit; OWASP CSV Injection; W3C WCAG 2.2. Reviewed October 14, 2026. Manual assistive-technology and cross-browser testing are still needed.

## Save and restore

Use **Save workspace JSON** to preserve your events and projection settings as a local file. **Restore workspace JSON** reopens a compatible file after confirmation. Files stay in the browser and are never uploaded. Restore accepts `.json` files up to 1,000,000 bytes, requires strict UTF-8, validates exact event IDs, amounts, recurrence and dates, and rejects unknown fields or unsupported versions. Invalid or canceled imports preserve current entries; successful restores clear old projections until recalculated. Store downloaded financial files securely.

Import validation references: [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) and [WCAG 2.2 Error Identification](https://www.w3.org/WAI/WCAG22/Understanding/error-identification). Reviewed October 14, 2026.
