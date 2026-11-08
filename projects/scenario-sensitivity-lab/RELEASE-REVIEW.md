# Scenario Sensitivity Lab — release review packet (2026-11-08 UTC)

## Decision
**Review candidate only. Not approved for publication.** This packet concerns the synthetic, one-category calculator in `index.html`, not the live website, ANA rate model, or any actual organizational forecast. Do not merge or publish based on this packet alone.

## Minimum viable scope
- Enter nonnegative whole-number baseline/proposed session counts (0–100,000) and fee amounts (0–1,000,000 dollars, at most two decimals).
- Recalculate baseline and proposed costs, total change, volume effect at baseline fee, and rate effect at proposed volume.
- Reject invalid entries, clear stale results, disable export, then recover on correction.
- Restore the fictional example and export a CSV containing entered assumptions and calculated values.
- Preserve the distinction between **fictional example**, **user-entered assumptions**, and **real forecast**. No persistence, remote calls, or claims of causal attribution.

## Reproducible review
Serve this directory locally, e.g. `python3 -m http.server 8765` from the repository root, then open `http://localhost:8765/projects/scenario-sensitivity-lab/browser-acceptance.html`. Select **Run browser checks**. This fixture checks arithmetic, cent precision, invalid entry/recovery, fractional count rejection, reset focus, and captured CSV Blob content. Its existence is **not** evidence that it passed. Capture the browser, date, source commit, and complete result before marking accepted.

Acceptance checklist:
- [ ] Fixture actually executed at this candidate commit; all checks passed or failures resolved.
- [ ] Downloaded CSV opened and independently inspected for correct rows, formula results, CSV escaping and no stale values.
- [ ] Keyboard-only traversal, visible focus, reset and export behavior checked.
- [ ] 320px viewport and enlarged-text reflow checked; no inaccessible content or horizontal page overflow.
- [ ] Invalid/empty/out-of-range inputs and correction tested in a served browser.
- [ ] Relevant exact-head CI checked once; unrelated portfolio failures recorded separately.
- [ ] Privacy reviewed: no remote input transmission, cookies, storage, or real fee data.
- [ ] Item-specific author approval documented before merge or WordPress publication.
- [ ] After authorized release, verify live URL, functionality and linked source commit.

## Known constraints
The calculator is a synthetic teaching exercise, not a general multi-category forecasting engine. It omits seasonality, cancellations, bursts, contractual exceptions and uncertainty intervals. The two effects sum algebraically because the decomposition is ordered volume-first; it is not a causal estimate. Browser acceptance, device/screen-reader testing and CI are not asserted by this packet. No production authorization is inferred from work on the branch.

## Release handoff
Source: `projects/scenario-sensitivity-lab/index.html`  
Fixture: `projects/scenario-sensitivity-lab/browser-acceptance.html`  
Status: **Ready for focused acceptance / author review**, unmerged and unpublished.  
Next: execute one served-browser acceptance pass; if it passes, request specific release approval and then verify the actual live deployment. If browser access is unavailable for two runs, park the external blocker and advance another item.
