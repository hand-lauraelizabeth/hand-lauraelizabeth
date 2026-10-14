# Cash Flow & Bill Timing Simulator

A browser-local planning tool for dated income, bills, and end-of-day projections. Compare a shifted payment date against the original baseline and export the scenario as CSV. No account, bank connection, or remote upload is required.

Use a local static HTTP server to serve this directory; JavaScript modules do not work reliably from file URLs. Run `node engine.test.mjs` for deterministic regression checks.

Amounts use integer cents. Monthly dates are clamped to the last calendar day when needed. The tool does not model settlement times, overdraft fees, or bank rules, and cannot provide financial determinations. CSV export adds apostrophes to suspicious textual cells; that precaution can change text and is not a universal guarantee.

Reference: CFPB Your Money, Your Goals toolkit; OWASP CSV Injection; W3C WCAG 2.2. Reviewed October 14, 2026. Manual assistive-technology and cross-browser testing are still needed.
