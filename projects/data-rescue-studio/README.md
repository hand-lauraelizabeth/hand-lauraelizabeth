# Data Rescue Studio

A browser-local CSV/TSV preview and review utility for students, researchers, community organizations, and small businesses.

**Supported in this preview:** open a UTF-8 CSV/TSV, inspect column completeness, detect exact duplicate rows without removing anything silently, preview records, optionally exclude exact duplicates from a copy, and export a CSV. The original file is not modified.

**Not yet supported:** multi-file joins, fuzzy record linkage, date standardization, Excel workbook import, or domain-specific quality rules. A duplicate means an identical entire row—not evidence that two people, transactions, or organizations are the same.

## Use

Open \`index.html\` in a browser and select a local \`.csv\` or \`.tsv\` file, or use the built-in fictional sample. Files are parsed in the browser. The current text limit is 5 MB, 50,000 data rows, and 100 columns. A malformed row with the wrong number of cells produces an error rather than silently dropping data. Output preserves original header labels and cell values except for options that are explicitly selected.

The **spreadsheet-oriented formula precaution** prefixes formula-like values with a tab inside their CSV field. This may modify data and is **not** a universal spreadsheet-injection defense. Disable it for machine-readable exports, inspect all untrusted data, and consult [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection). There is no cross-application perfect CSV sanitization. Nothing is uploaded to the website server by this local demo.

## Test

\`\`\`bash
node projects/data-rescue-studio/tests/rescue-core.test.js
\`\`\`

Includes synthetic fixtures for quoted commas, embedded newlines, repeated quotes, Unicode BOM, tabs, blank values, repeated headers, exact duplicates, and malformed rows.

## Sources and design references

- [OpenRefine](https://openrefine.org/) — established free data-cleaning software with a much broader feature set.
- [OWASP — CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection) — formula risk and limitations of mitigations.
- [OWASP — File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) — untrusted file-handling patterns.
- [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/) — access and error feedback requirements.

This tool makes no claim to replace a full statistical, ETL, or reconciliation environment.
