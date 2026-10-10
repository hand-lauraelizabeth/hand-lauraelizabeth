# College Search — execution status

Last updated: 2026-10-10T03:37:42.864Z UTC
Repository branch: `feature/college-search-sprint1-20261009`
Production release: **BLOCKED** until Sprint 1 staging, source integrity, performance, manual QA, and explicit owner approval are complete.
WordPress production page 1044 remains **Draft**; do not publish without approval.

## Operating rules
- Execute exactly **one** first not-done/not-blocked task per hourly run; verify with evidence, commit to the Sprint 1 branch, update this file, stop.
- Move past human-decision blockers only after recording the precise question.
- Do not rewrite Git history, delete source data, or publish production without new explicit approval.
- Do not reactivate unreviewed NY20 evidence. No fallback school data in the MVP.
- Sprint 2 begins only after Sprint 1 is live. A staged page is not live production.

## Task queue (strict order)
| # | Task | Status | Evidence / blocker |
|---|---|---|---|
| 1 | Resolve `national-00.json` SHA-256 mismatch; determine cause or rebuild manifest | DONE | The committed `national-00.json` hashes to `3719b6345f9af3a0d1385334bea689162b1a5697be869749733d660bd1c52d1f`, **equal** to the manifest value. The integrity test now always targets the committed national source rather than an optional alternate `tests/shards` folder, and checks the public-only NY institution directory instead of removed NY20 evidence. GitHub Actions [run 38020357137](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/38020357137), job `114119785207`, recorded **10 national snapshot tests passed (0.045 s)**. No manifest rebuild or data deletion warranted. Commit `7c7f1403aa0dc6df66d94c9524a6788ad971992b`. |
| 2 | Create minified one-file national JSON keyed by UNITID; only UNITID/name/city/state/URL; gzip and report count/size | DONE | Checked-in keyed JSON and gzip: **6,243** unique UNITIDs, **732** null URLs, **725,379** JSON bytes, **179,675** gzip bytes (**175.46 KiB**); under 500 KiB compressed target. **GitHub Actions validation PASSED**: [run 38020799987](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/38020799987), job `114121148298`; Python `--check` verified all 13 source shard checksums, exact keyed data, 6,243 records, and gzip decompression. JSON SHA-256 `b18fa5a4be6f5d7a1c70d93d13009a10d1ef7757fa289c1af07856d263320539`; gzip SHA-256 `437a28a8cd90df2bbf7e2b4bb43abacb875f4d8b9417248dd3d0f4b3ed4ba379`. Git blobs `b115fa7c`/`d1f0a8e5`. |
| 3 | Standalone dependency-free component: name/state/sort/count/Clear/pagination/loading/error/Retry; no fallback | DONE | Standalone `college-search-sprint1.html`, one national JSON request, default 24 visible results, accessible control labels, loading/error/Retry and no fallback. [GitHub Actions browser smoke run 38021177084](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/38021177084), job `114122288926` **PASSED**: browser loaded 6,243 real Scorecard institutions; verified name search, NY state/zero results, ascending/descending sort, live count, Clear, 24-to-48 Show more, disabled controls while loading, visible request-failure state with no fallback, and successful Retry; zero uncaught page errors. JavaScript `node --check` passed. |
| 4 | Unit tests for name, state, combination, sort, zero results and Clear | TODO | |
| 5 | Accessibility: zoom, all labels/links, main landmark, focus and zero console errors | TODO | |
| 6 | One collapsed About this data note — June 10, 2026 College Scorecard | TODO | |
| 7 | Private staging deployment; three Lighthouse mobile runs and median | TODO | LCP <3 seconds; assess exceptions separately if needed |
| 8 | Fix measured LCP/performance budget misses, using visible-page rendering | TODO | |
| 9 | Write manual desktop/iOS/Android click-through script and rollback note | TODO | |
| 10 | Notify owner staging is ready; await approval for publication | TODO | Stop; never publish without approval |
| 11 | Sprint 2 control/locale/size after Sprint 1 production approval | BLOCKED | Human approval and live Sprint 1 required |

## Decisions and known constraints
- PR #6 merged as `240ce2595f5f4fb177af50b20f997de33cbe8827`; unapproved NY20 evidence removed from `main` and old WordPress page 1044 set to Draft.
- Do not rewrite Git history unless a confidentiality obligation is confirmed.
- Sprint 1 scope is **only** name, state, sort, result count and Clear.
- One compressed file or justified lazy loading; a visible loading state and error/Retry required.
- Address, ZIP, radius and richer filters are later sprints, not Sprint 1.
- LCP <3 seconds and zero console errors remain release gates; CLS/TBT may be nonblocking if necessary.
- Only private staging page and page 1044 may be changed.

## Latest run
- **2026-10-10T03:37:42.864Z — Task #3 DONE.** Committed `college-search-sprint1.html` (plain HTML/CSS/JS, no dependencies). All five user-facing MVP controls (name, state, sort, count, Clear), Show more, loading feedback and error/Retry are wired to the 6,243-school national JSON asset. [GitHub Actions browser smoke run 38021177084](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/38021177084), job `114122288926` **PASSED**: browser loaded 6,243 real Scorecard institutions; verified name search, NY state/zero results, ascending/descending sort, live count, Clear, 24-to-48 Show more, disabled controls while loading, visible request-failure state with no fallback, and successful Retry; zero uncaught page errors. JavaScript `node --check` passed. **Next task: #4 — unit tests for filter logic (name/state/combination/sort/zero/Clear).** No staging or production WordPress changes.
- **2026-10-10T03:30:17.105Z — Task #2 DONE.** Created `data/sprint1/college-search-national.v1.json` and genuine `.json.gz` from the 13 validated June 10, 2026 College Scorecard shards. **6,243 unique UNITIDs**, **59 state/territory codes**, **732 URL values preserved as unknown (null)**; JSON **725,379 bytes**, gzip **179,675 bytes / 175.46 KiB** (well under 500 KiB). Added `build_sprint1_national.py --check` for source/checksum/count and gzip round-trip validation, plus dedicated CI. **GitHub Actions validation PASSED**: [run 38020799987](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/38020799987), job `114121148298`; Python `--check` verified all 13 source shard checksums, exact keyed data, 6,243 records, and gzip decompression. JSON SHA-256 `b18fa5a4be6f5d7a1c70d93d13009a10d1ef7757fa289c1af07856d263320539`; gzip SHA-256 `437a28a8cd90df2bbf7e2b4bb43abacb875f4d8b9417248dd3d0f4b3ed4ba379`. No WordPress or production changes. **Next task: #3 — standalone dependency-free component.**
- **2026-10-09 23:25 EDT — Task #1 DONE.** Commit `7c7f1403aa0dc6df66d94c9524a6788ad971992b` repaired national test source selection and replaced the test's dependency on removed private NY20 evidence with a public-only identity check. GitHub Actions run [38020357137](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/38020357137) reports **10 national snapshot tests passed**, including checksums, 6,243 national records and unique UNITIDs. Direct repository-text SHA-256 of national-00.json is identical to the existing manifest. **Next task: #2 — build minified keyed national asset and report gzip size/count.** Do not re-run completed task #1.
- **Independent CI blocker:** The **overall workflow is not green**: downstream `test_ny20_live_projection.py` fails `FileNotFoundError` because it still expects the deliberately deleted `data/ny20-institution-evidence.v1.json`. This legacy test must be changed to a public-only fixture or retired as part of the pre-staging CI gate; do **not** restore unreviewed NY20 data. This failure is unrelated to the now-passing national SHA integrity test.
- **Deployment status:** WordPress production page 1044 Draft; no staging deployment or production publication performed. No human approval question currently blocks task #4.
