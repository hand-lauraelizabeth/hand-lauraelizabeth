# College + Career Matcher — admissions-evidence review candidate (2026-11-03)

Review-only interactive preview: https://raw.githack.com/hand-lauraelizabeth/hand-lauraelizabeth/review/matcher-ny20-contained-fixture-ci-20261102-11et/projects/college-career-matching/admissions-evidence-review.html

## What works
- Select Hunter College Generic BS Nursing, Accelerated Second-Degree Nursing, or RN-to-BS to display pathway-specific admissions evidence and official source links.
- Compare three pathways in a keyboard-focusable, labeled, horizontally scrollable table with a visible focus ring and responsive overflow.
- Distinguish general college test-optional policy, nursing-specific examinations, RN license prerequisites, and not-yet-independently-established facts.
- Avoid implying historical CIP completions demonstrate current program offerings, admission, licensure, or eligibility.

## Independent release gate
- Exact implementation head b9f960ade3b3515107407a451785a04a4ec646f5.
- College matcher validation run https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/41599729298 SUCCESS. Job 125795355134 dedicated Chromium/axe step SUCCESS; log: 'PASS: three pathway interactions, source links, mobile table, keyboard focus, axe serious/critical=0'.
- Portfolio validation run https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/41599729292 SUCCESS.
- These are CI-hosted browser tests of the review artifact, **not** proof that the raw.githack-hosted URL has been independently opened or rendered. Hosted URL check remains pending.

## Scope and release restrictions
Review branch only; no merge or WordPress production deployment. Historic NY20 evidence remains intentionally removed; eight retired projection tests remain explicitly skipped. No new private records, inferred licensure, or unapproved crosswalk. Review admission pages and current-cycle requirements before any future public claims. Production publication requires explicit user approval.
