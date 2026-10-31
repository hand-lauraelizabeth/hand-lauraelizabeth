# Community Data Explorer

A free, browser-local workspace for reviewing **user-supplied** American Community Survey (ACS) estimates. Open `index.html` from a local HTTP server or a reviewed static hosting preview. No account or server-side upload is required. The tool does not download official Census observations, certify their authenticity, or make statistical significance determinations.

## Prepare your data

Save a UTF-8 CSV with these columns **in this exact order**:

```csv
source_id,geography,variable,series,period_start,period_end,estimate,moe
SYN-0001,"Example area, ST",B19013_001E,acs5,2015,2019,60000,1000
SYN-0002,"Example area, ST",B19013_001E,acs5,2020,2024,70000,1200
```

**These two records are fictional testing examples, not Census statistics.** `source_id` is a user-assigned, unique identifier and is preserved exactly, including leading zeroes. `geography` must use consistent labels for matching; labels are not verified against Census geographic codes. `variable` must use an ACS detailed-table estimate ID (for example, `B19013_001E`); the tool checks the identifier's syntax, not its meaning or availability for a given year. `series` is `acs1` or `acs5`. A 5-year period must cover five calendar years. The standard 2020 ACS 1-year release is not accepted.

`estimate` and `moe` accept nonnegative whole numbers, decimals with up to six fractional places, or explicit missing markers. ACS B01002 median age, for example, uses decimal values. The export retains original strings and adds `difference_exact` calculated using decimal-string arithmetic, avoiding floating-point subtraction artifacts. The existing `difference` numeric field remains for compatibility only when JavaScript Number conversion preserves the displayed decimal digits; otherwise it is `null` with a visible caution, and `difference_exact` remains authoritative. The preview displays original estimate/MOE strings, not potentially rounded numeric conversions. Parsed numeric estimate/MOE fields are conveniences and may lose digits at high magnitudes: use `estimate_raw` and `moe_raw` for exact source evidence. Blank fields and `null` are **missing**. Official Census annotation sentinels (`-999999999`, `-888888888`, `-666666666`, `-555555555`, `-333333333`, `-222222222`, including documented `.0`/`.00` variants) and corresponding textual markers (`N`, `(X)`, `-`, `*****`, `***`, `**`) are preserved verbatim and classified in separate `estimate_status` and `moe_status` fields. A controlled MOE (`-555555555`/`*****`) is **not** silently treated as numeric zero. Unrecognized annotations and MOE-only codes in an estimate field are rejected. Unsupported negative values are rejected rather than silently converted. File size is limited to 2,000,000 bytes and 5,000 records; invalid UTF-8, malformed quoting, duplicate source IDs and control/directional characters in IDs are rejected.

## Review and export

After importing, select two source IDs. The comparison gate blocks mixed ACS 1-year/5-year series, different variables, overlapping periods for the same geography, different periods for different geographies, and missing estimates. A permitted difference is **arithmetic only**; it is not a significance finding, inflation adjustment, or proof of change. Review margins of error and changing definitions before interpreting results.

Export **JSON** to retain original numeric strings, exact IDs, missing-value markers, selected comparison, a user-supplied (unverified) dataset label, and—when WebCrypto is available—an SHA-256 fingerprint of the original file bytes. A fingerprint establishes byte identity, **not** Census authenticity. When WebCrypto is unavailable, the export explicitly records that no fingerprint was computed.

If a browser blocks the JSON download, the page displays a focused recovery message without exposing local filenames or source identifiers. Your imported records and comparison remain available for another attempt. A successful download click means the download **started**; confirm that the browser saved the file before relying on it. Temporary browser download links and object URLs are cleaned up after attempts.

There is no spreadsheet CSV export, to avoid turning untrusted source values into executable formulas. Uploaded data is processed locally in the browser; the application code does not issue network requests. The optional Census guidance link navigates away only if selected.

## Official interpretation guidance

- [Census Bureau: Comparing ACS Data](https://www.census.gov/programs-surveys/acs/guidance/comparing-acs-data.html)
- [Census Bureau: Why margins of error matter](https://www.census.gov/help/topics/faq.do-i-need-to-consider-the-margins-of-error-when-comparing-acs-estimates.html)
- [Census Bureau: ACS estimate and annotation values](https://www.census.gov/data/developers/data-sets/acs-1year/notes-on-acs-estimate-and-annotation-values.html)

These Census resources were reviewed October 24, 2026. JavaScript precision guidance was additionally reviewed October 30, 2026: [MDN: Number](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number). The Census annotation table explicitly distinguishes suppressed, not-applicable, insufficient-sample, controlled, and open-ended-median values; the tool preserves these distinctions without making a statistical inference. The tool remains under review; automated tests do not establish full accessibility or suitability for high-stakes decisions.
