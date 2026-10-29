# Data Rescue Studio

A browser-local CSV/TSV preview and review utility for students, researchers, community organizations, and small businesses.

**Supported in this preview:** open a UTF-8 CSV/TSV, inspect column completeness, detect exact duplicate rows without removing anything silently, preview records, optionally exclude exact duplicates from a copy, and export a CSV. The original file is not modified.

**Also supported in this review:** independently import a second UTF-8 CSV/TSV file and select one identifier column in each table. Exact, case-sensitive key comparison classifies one-to-one matches, nonmatching keys, missing keys, and ambiguous (repeated) keys. Ambiguous identifiers are never automatically merged. Export a separate audit CSV with the classification, identifier, and logical source record numbers. This file is also generated locally, and may contain sensitive identifiers.

**Source-record issue review:** the first-file page includes keyboard-operable filters for all original source records, records with blank or whitespace-only cells, and repeated exact records. Each preview row identifies its original logical source record; repeated records also identify the first identical source record. Filtering changes only the on-screen preview, never downloaded data. The optional deduplication checkbox affects the CSV copy, not the original-record preview or exact JSON evidence. Records are displayed 20 per page with Previous/Next controls, an explicit total, and a keyboard-operable jump to an original logical source-record number. A successful jump moves focus to the exact source-row header and marks it with a visible “Jump target” label; it does not add a permanent Tab stop or change downloaded data. Changing filters, paging, or editing the jump field clears the old marker. A record excluded by the current filter is not shown; change the filter to locate it. No fuzzy or semantic duplicate judgment is made.

**Not yet supported:** merged/joined output tables, fuzzy record linkage, date standardization, Excel workbook import, or domain-specific quality rules. The tool does not infer that matching keys establish that two entities really are the same. A source record number counts CSV/TSV records (including the header as record 1); quoted multiline cells may span multiple physical lines. A duplicate means an identical entire row—not evidence that two people, transactions, or organizations are the same.

## Use

Open \`index.html\` in a browser and select a local \`.csv\` or \`.tsv\` file, or use the built-in fictional sample. Files are parsed in the browser. The current text limit is 5 MB, 50,000 data rows, and 100 columns. A malformed row with the wrong number of cells produces an error rather than silently dropping data. Output preserves original header labels and cell values except for options that are explicitly selected.

The **spreadsheet-oriented formula precaution** prefixes formula-like values with a tab inside their CSV field. This may modify data and is **not** a universal spreadsheet-injection defense. Disable it for machine-readable exports, inspect all untrusted data, and consult [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection). There is no cross-application perfect CSV sanitization. Nothing is uploaded to the website server by this local demo.

## Local file validation

Both the primary review page and the transformation/reconciliation review page validate the imported CSV/TSV **as bytes**. The file must have a `.csv` or `.tsv` extension, be at most **5,000,000 bytes** (decimal 5 MB), and decode as valid UTF-8. Invalid UTF-8 sequences and embedded NUL characters are rejected with a visible error; UTF-8 BOMs are supported. Malformed CSV/TSV rows still fail without silently discarding data. Filename extensions and browser-supplied media types do not prove that a file is safe. No file is sent to a remote server.

These decisions follow [MDN's TextDecoder documentation](https://developer.mozilla.org/en-US/docs/Web/API/TextDecoder/TextDecoder) for fatal decoding and the [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) for allowlisted extensions, content validation, and size limits. The separate spreadsheet-oriented formula precaution remains **best-effort**, modifies exported values, and is not a substitute for inspecting untrusted CSVs.

## Transformation and source-position review

The separate review page `history-preview.html` combines local CSV/TSV import, reversible whitespace trimming, exact duplicate removal, undo/redo, two-file exact-key comparison, and downloadable CSV and JSON evidence. Select a first-file identifier and second-file identifier, then choose **Compare identifiers**. After changing the first-file working copy, rerun the comparison. The original file is not modified.

The comparison audit records **original logical CSV/TSV record numbers**, including after duplicate removal. Record 1 is the header; embedded line breaks inside quoted fields do **not** start a new logical record. Ambiguous matches and missing identifiers remain explicit and are not silently joined. A comparison key is treated as an exact string, not proof that two records describe the same entity.

The operations JSON stores action types, affected-row counts, column positions, revision status and export settings, but not input cell values. It is not a backup or an authenticated record of the source file: users must keep the original file to reproduce the workflow. Audit CSVs include keys, which may be private. Spreadsheet-oriented formula prefixes can alter cell values and are not a guaranteed defense across applications. This review feature is not yet embedded in the primary `index.html` page.

## Test

\`\`\`bash
node projects/data-rescue-studio/tests/rescue-core.test.js
node projects/data-rescue-studio/tests/rescue-ui-contract.test.js
node projects/data-rescue-studio/tests/reconcile-core.test.js
node projects/data-rescue-studio/tests/reconcile-regression.test.js
node projects/data-rescue-studio/tests/reconcile-ui-integration.test.js
node projects/data-rescue-studio/tests/history-core.test.js
node projects/data-rescue-studio/tests/provenance-core.test.js
node projects/data-rescue-studio/tests/file-reader.test.js
\`\`\`

Includes synthetic fixtures for quoted commas, embedded newlines, repeated quotes, Unicode BOM, tabs, blank values, repeated headers, exact duplicates, malformed rows, missing and ambiguous keys, and second-file state changes.

An additional independent CSV/TSV interoperability check can be run with `node projects/data-rescue-studio/tests/cross-language-csv.test.cjs` (requires Python 3). It compares browser-engine exports against Python's standard-library `csv.reader`, then imports Python `csv.writer` output into the browser engine across 600 deterministic synthetic cases. It also checks exact retained source-record positions. This does **not** establish Excel or Google Sheets reopen-and-resave safety; those require separate application testing. The synthetic controller test is not a substitute for real-browser keyboard, mobile, and zoom checks.

## Sources and design references

- [OpenRefine](https://openrefine.org/) — established free data-cleaning software with a much broader feature set.
- [OWASP — CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection) — formula risk and limitations of mitigations.
- [OWASP — File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) — untrusted file-handling patterns.
- [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/) — access and error feedback requirements.

This tool makes no claim to replace a full statistical, ETL, or reconciliation environment.
