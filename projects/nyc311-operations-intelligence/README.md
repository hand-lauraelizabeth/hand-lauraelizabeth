# Public Service Operations Intelligence · NYC 311

This public-data study examines how service-request records can inform operational questions about demand, geography, workload, and closure patterns. It is an independent research demonstration; it does not represent work commissioned by New York City or reveal employer records.

## Source and reproducibility

- Source: [NYC Open Data, 311 Service Requests from 2020 to Present](https://data.cityofnewyork.us/d/erm2-nwe9), dataset `erm2-nwe9`. For earlier years, use the separate [2010–2019 archive](https://data.cityofnewyork.us/d/76ig-c548), not the current endpoint.
- The source was split in December 2025; the portal's *Problem* and *Problem Detail* headings retain the API field names `complaint_type` and `descriptor`.
- Save an official CSV export to your machine; it is **not** included in the repository. Run `python pipeline.py 311_export.csv aggregates.json --as-of 2026-10-15` using the downloaded snapshot and set `--as-of` to the snapshot date, not an unrelated current date.
- Run `python -m unittest -v test_pipeline.py` for deterministic contract tests. The tests use fabricated records and do not establish any findings about NYC operations.
- Outputs include a SHA-256 hash of the source bytes, the exact input count, nonfatal data-quality exceptions, and display-safe aggregates by month, borough, agency, and original problem category.

## Interpretation limits

Closure status marks an administrative workflow state, not confirmed issue resolution. The initial pipeline deliberately does **not** compute agency rankings, performance targets, causal effects, or geographic population-normalized rates. It does not perform a full unique-key collision audit or case-mix adjustment. Small aggregate cells are suppressed, and individual addresses, coordinates, ZIP codes, and complaint details never enter output. No conclusions should be drawn from fixture tests.

## Development sequence

The next stage will add scalable DuckDB duplicate-key auditing, monthly closure-duration distributions, published time-window denominators, validated multi-year ingestion, and a responsive staging visualization. No WordPress production content or existing national college-search data is changed by this repository project.
