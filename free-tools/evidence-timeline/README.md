# Evidence & Timeline Builder (review prototype)

A free, browser-local tool for organizing dated notes and source references. No account, server storage, or remote upload is required. Open `index.html` from a static web server, then add a unique source ID, calendar date, description, evidence type, review status, and optional group label.

Records appear in chronological order. Matching group labels identify records that may need human comparison; the tool does **not** determine whether claims conflict or whether evidence is authentic. The statuses are assigned by the person entering the records, not verified by software.

**Exports:** CSV is designed for spreadsheet viewing and adds a leading apostrophe to some formula-like values; this changes the exported field and is not universally reliable after spreadsheet save/reopen. JSON preserves entered descriptions and other normalized record values. Source IDs, descriptions, and group labels are preserved exactly, including leading/trailing whitespace; identifiers must be unique as entered. Download files should be handled as sensitive records.

**Privacy:** Data stays in the current tab and disappears on refresh or close. The page contains no analytics or remote dependencies. This prototype accepts typed entries and JSON files exported by this tool (5,000,000-byte limit, strict UTF-8 and schema validation). Import replaces the current timeline only after confirmation. It does not read attachments or medical records.

**Testing:** `node core.test.mjs` covers the original chronology; `node exact-import.test.mjs` covers exact IDs, schema and file limits. The import UI uses local files only. `python browser_smoke.py` runs 15 synthetic Chromium assertions (requires Playwright and Chromium at the configured executable path). The browser harness injects the same source files into an isolated page because the development runtime blocks local navigation; it does not verify deployment CSP, real HTTP loading, screen readers, or other browser engines.

Accessibility review follows W3C WCAG 2.2 labels/instructions and text-error guidance: https://www.w3.org/TR/WCAG22/ . CSV risks and the limitations of mitigations are documented by OWASP: https://community.owasp.org/attacks/CSV_Injection .

**Review only:** No legal, medical, or financial determinations; not published to production.

**Import note:** The JSON import is all-or-nothing. Invalid files leave existing records unchanged. Export before replacing a timeline. Manual screen-reader, cross-browser, and deployed CSP checks remain release requirements.
