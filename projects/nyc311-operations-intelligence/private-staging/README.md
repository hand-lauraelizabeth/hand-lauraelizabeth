# NYC 311 aggregate viewer model

This review-only JavaScript module validates disclosure-screened pipeline JSON and filters released cells for a future interactive view. It rejects raw fields, small cells, duplicate grains, and unsafe closure partitions. It does not establish source completeness or citywide totals. Run `node --test test_model.mjs`.

The official September 2026 Socrata count query returned 323,627 on October 15, 2026 ET; this mutable count is not a pinned export. Source: https://data.cityofnewyork.us/resource/erm2-nwe9.json . No raw source or WordPress production edits are included.
