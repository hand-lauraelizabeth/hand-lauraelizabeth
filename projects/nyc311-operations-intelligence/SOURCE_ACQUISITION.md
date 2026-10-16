# NYC 311 monthly source acquisition (private)

Official dataset: https://data.cityofnewyork.us/d/erm2-nwe9
SODA2 paging: https://dev.socrata.com/docs/paging.html
NYC API guide: https://www.nyc.gov/opendata/get-started/user-guides/open-data-apis

From this directory, run:

    python source_export.py --month 2026-09 --output private/nyc311-2026-09-20261016.csv

The command queries the exact month using source calendar_date fields\n(serialized as local date-time strings),
selects seven non-location fields, pages by strictly increasing unique_key,
and reconciles counts before and after retrieval. It refuses repeated or
out-of-order keys, truncated pages, changed counts and existing outputs.
It saves a SHA-256 manifest with the query, retrieval time and limitations.
The source is mutable; equal counts do not prove an immutable snapshot.

Optional --expected-count N is valid only for an independently verified count
of the exact query. The October 15 count of 323,627 is not a permanent total.
Next, run snapshot_audit.py and pipeline.py with --expected-rows N, using the
verified manifest count. Keep raw CSV, manifest and QA outside GitHub.
Only disclosure-screened aggregates may be considered for private staging.
Do not publish to WordPress without approval. Tests use synthetic records.
