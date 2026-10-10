# College Search — execution status

Last updated: 2026-10-09 (America/New_York)
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
| 1 | Resolve `national-00.json` SHA-256 mismatch; determine cause or rebuild manifest | IN_PROGRESS | Direct GitHub connector read of `national-00.json` produced SHA-256 `3719b6345f9af3a0d1385334bea689162b1a5697be869749733d660bd1c52d1f`, matching `manifest.v1.json`. Prior GitHub Actions national test reported a mismatch; cause must be established and CI repaired. |
| 2 | Create minified one-file national JSON keyed by UNITID; only UNITID/name/city/state/URL; gzip and report count/size | TODO | 6,243 expected unique UNITIDs |
| 3 | Standalone dependency-free component: name/state/sort/count/Clear/pagination/loading/error/Retry; no fallback | TODO | |
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
- 2026-10-09: initialized state file. Task #1 in progress; no launch authorized.
