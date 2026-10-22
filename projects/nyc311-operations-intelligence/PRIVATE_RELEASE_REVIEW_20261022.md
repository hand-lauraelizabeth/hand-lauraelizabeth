# Private release review — 22 October 2026

Status: HOLD. Do not publish or merge as a release authorization.

A candidate aggregate can leak suppressed cohort counts when an exact overall total and displayed group counts are both published. The hidden residual is the difference. Even when two hidden groups cannot be separately solved, their combined total is exact. Comparing releases can expose small residual changes or a closure count crossing the visibility threshold.

Required gate: inspect exact residual exposure, small residual, residual change, suppression structure change, closure visibility transition, and small quality-metric differences. This review does not establish safety against external public cross-tabs, integer constraints, or other releases. Use only synthetic fixtures in repository tests. Official source: https://data.cityofnewyork.us/d/erm2-nwe9 .

Source verification date: 2026-10-22. No production or staging publication authorized.
