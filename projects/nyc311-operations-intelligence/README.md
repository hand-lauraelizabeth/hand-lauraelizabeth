# Public Service Operations Intelligence · NYC 311

This public-data study examines how service-request records can inform operational questions about demand, geography, workload, and closure patterns. It is an independent research demonstration; it does not represent work commissioned by New York City or reveal employer records.

## Source and reproducibility

- Source: [NYC Open Data, 311 Service Requests from 2020 to Present](https://data.cityofnewyork.us/d/erm2-nwe9), dataset `erm2-nwe9`. For earlier years, use the separate [2010–2019 archive](https://data.cityofnewyork.us/d/76ig-c548), not the current endpoint.
- The source was split in December 2025; the portal's *Problem* and *Problem Detail* headings retain the API field names `complaint_type` and `descriptor`.
- For a private reporting-month acquisition, run `python source_export.py --month 2026-09 --csv /private/311_2026_09.csv --receipt /private/311_2026_09_receipt.json` **only on a private, networked host**. Neither the seven-column CSV nor its receipt belongs in this repository. The exporter rejects publisher drift and source cross-aggregate disagreement, but its paginated API reads are not transactional.\n- Independently check those private files with `python source_receipt_audit.py /private/311_2026_09.csv /private/311_2026_09_receipt.json`. It recomputes file, row, key, month, and borough×agency digest checks. **Exit status 2 and publication HOLD are expected even when all internal checks pass**; a self-consistent receipt is not proof of official immutable source provenance.\n- The separate `pipeline.py` ingests a privately authenticated CSV and supports `--reporting-month`, `--expected-sha256`, and `--expected-rows`. Set `--as-of` to the actual source snapshot date, not an unrelated current date. Do not release its fine-grained aggregates without the independent disclosure gates.
- Run `python -m unittest -v test_pipeline.py` for deterministic contract tests. The tests use fabricated records and do not establish any findings about NYC operations.
- Outputs include a SHA-256 hash of the source bytes, the exact input count, nonfatal data-quality exceptions, and display-safe aggregates by month, borough, agency, and original problem category.

## Interpretation limits

Closure status marks an administrative workflow state, not confirmed issue resolution. The initial pipeline deliberately does **not** compute agency rankings, performance targets, causal effects, or geographic population-normalized rates. It checks exact within-file unique-key collisions, but does not authenticate source provenance or perform case-mix adjustment. Small aggregate cells are suppressed, and individual addresses, coordinates, ZIP codes, and complaint details never enter output. No conclusions should be drawn from fixture tests.

## Development sequence

Next steps are an authenticated full source-cohort capture, independent source and 20-cell editorial grouping reconciliation, integer and temporal disclosure audits, native accessibility testing, and private staging. Longer-term work may include validated multi-year ingestion and denominators. No WordPress production content or existing national college-search data is changed by this repository project.
