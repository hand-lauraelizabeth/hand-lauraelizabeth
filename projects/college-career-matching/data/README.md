# Generated Data

This directory is reserved for local or CI-generated College + Career Matching Tool data products.

Generated contents are intentionally not committed:

- `snapshots/` — immutable raw-source snapshots plus per-snapshot normalized tables and QA reports;
- `normalized/` — optional consolidated normalized tables;
- `reports/` — cross-source QA and join reports.

The ingestion prototype writes each source snapshot under:

`snapshots/<source_id>/<UTC timestamp>/`

Each snapshot contains the raw source file/response, `source_snapshot.json` with SHA-256 and release metadata, normalized output where an adapter is implemented, and `reports/qa.json`.

Public federal source data can always be reacquired from the URLs and versions in `../source_manifest.json`; keeping generated datasets out of Git avoids bloating repository history and makes source lineage explicit.
