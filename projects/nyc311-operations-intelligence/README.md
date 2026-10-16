# Public Service Operations Intelligence · NYC 311

This public-data study investigates how administrative service-request records can inform questions about demand, workload, geography, and closure patterns. It is an independent research demonstration, not an assessment commissioned by New York City.

## Source and method

The source is [NYC Open Data, 311 Service Requests from 2020 to Present](https://data.cityofnewyork.us/d/erm2-nwe9), dataset `erm2-nwe9`. The City maintains a [separate 2010–2019 archive](https://data.cityofnewyork.us/d/76ig-c548). Its [dataset update notice](https://www.nyc.gov/opendata/news/all-news/311-Service-Requests-Updates) confirms the split and explains that the displayed *Problem* label retains the API name `complaint_type`. The official [dataset dictionary](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data) identifies `unique_key` as the service-request identifier and lists `created_date` and `closed_date` as floating timestamps.

A source export is **not** included in this repository. The scripts operate on an official CSV downloaded locally and keep request identifiers in a temporary, local SQLite uniqueness index. They never export individual requests, locations, or addresses. To reproduce a specific analysis, record the export retrieval date, query/filter, row count and SHA-256 hash separately from the public aggregate file.

```bash
# Local source QA (keep the report private).
python snapshot_audit.py 311_export.csv --output-json private_source_qa.json

# Public-safe aggregate file, after checking source scope and count.
python pipeline.py 311_export.csv public_aggregates.json --as-of 2026-10-15

# Fabricated-record contract and integration tests; no official dataset required.
python -m unittest discover -p 'test_*.py' -v
```

When an independently established row count is available for the exact source query, add `--expected-rows N` to both commands, replacing `N` with that verified count. Otherwise disclose that completeness remains unverified. `--as-of` is an analyst-selected cutoff date, **not** proof of when the CSV was downloaded.

The pipeline rejects an export with blank or duplicate `unique_key` values or an expected-row mismatch before writing public aggregates. It does not silently deduplicate service requests. The offline QA index is disk-backed so the full set of identifiers need not reside in memory. Source floating timestamps are evaluated without inventing a timezone; timezone-qualified or invalid closure timestamps do not contribute to valid closure intervals. Private QA reports count invalid, reversed, future, zero-length and unusually long intervals. Closure requires a `Closed` status and a nonnegative interval ending on or before the analysis cutoff.

## Disclosure and interpretation

The public JSON contains only month × borough × agency × problem cells above a minimum count. It omits suppressed cells and exact source marginal totals; closure counts are also withheld unless both the closed and nonclosed partitions meet the minimum. Source QA counts remain private. Do not derive or publish unsuppressed totals alongside these cells, since they could expose withheld small counts.

Closure is an administrative state, **not** independent evidence that a condition was resolved. The present work does not establish response quality, agency rankings, population-normalized rates, causal effects, or differences adjusted for request type. File-internal uniqueness checks do not establish that an export contains every record in the official dataset. The repository's synthetic tests verify software behavior; they are not findings about NYC service delivery.

## Next validation

Run the audit on a dated, pinned official export and reconcile its scope and row count against the City's source query. Only then evaluate duration distributions, request-type comparability, and a keyboard-accessible, responsive visualization in private staging. No production WordPress pages or College + Career Matcher data are modified by this work.


## Monthly API acquisition: nullable fields

The official `erm2-nwe9` dataset identifies `unique_key` as text and `closed_date` as a timestamp that may be empty for an open request. The SODA JSON API can omit empty properties. The monthly keyset exporter therefore requires nonblank `unique_key` and `created_date` but preserves missing or null optional columns as empty CSV cells. Its **private** manifest counts normalized optional values by field. Unexpected nested/non-text values still fail closed; the offline audit decides whether the resulting date/status combinations are usable.

Source: [NYC Open Data dataset dictionary](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data); [Socrata SODA API](https://dev.socrata.com/docs/endpoints). Verified 2026-10-16. This change has synthetic regression coverage, not yet an official September 2026 CSV run.

## Monthly export scope validation

The source dataset defines `created_date` as a **floating timestamp**. The keyset exporter checks every returned date against the requested calendar month's inclusive start and exclusive next-month boundary; malformed, timezone-qualified and out-of-scope rows fail the entire export before either final file is created. This checks the records actually received, not completeness of the City's mutable dataset. The private manifest records the rule. Independent synthetic tests cover both boundaries and rejection cases. Source: [NYC Open Data field dictionary](https://data.cityofnewyork.us/resource/erm2-nwe9), [Socrata pagination documentation](https://dev.socrata.com/docs/paging.html); reviewed 2026-10-16. A real September 2026 bulk extract is still pending.
