# College Search Sprint 1 — Manual Device QA and Safe Rollback

**Status:** TEST PLAN ONLY — NOT EXECUTED / NOT RELEASE-APPROVED. Sprint 1 Task 9 creates instructions and verification criteria; it does **not** certify that desktop, physical iOS Safari, or physical Android Chrome has passed.

**Scope:** National College Search for 6,243 institutions (College Scorecard June 10, 2026 snapshot) on **private WordPress Draft page 1154**. Old explorer page **1044 remains Draft**. Production publication is blocked until explicit owner approval.

## 1. Private staging preparation

1. Sign in to WordPress as an authorized editor. Open [page 1154 in the WordPress editor](https://www.lauraelizabethhand.com/wp-admin/post.php?post=1154&action=edit) and select **Preview**. Direct preview candidate: https://www.lauraelizabethhand.com/?page_id=1154&preview=true . An authenticated preview nonce may be required; anonymous 404 is expected, not evidence of a working or broken authenticated page.
2. Verify **page 1154 = Draft**, **page 1044 = Draft**, and public parent page **452 unchanged** before and after testing. Do not alter any other page or publish the Draft.
3. Confirm the expected pinned dataset request: https://cdn.jsdelivr.net/gh/hand-lauraelizabeth/hand-lauraelizabeth@557c1350efd82001564745a1ef0922295b99625d/projects/college-career-matching/data/sprint1/college-search-national.v1.json . Expected HTTP 200, CORS allowed, **6,243 records**, one initial request.
4. Use a desktop browser (Chrome or Edge), a **physical iPhone with Safari**, and a **physical Android phone with Chrome**. Log device model, OS/browser version, viewport, browser settings and date. Device simulation is supplemental, not a replacement for physical mobile QA.
5. Keep screenshots, preview nonce URLs, cookies, private page details, and session data in a **private** evidence location. Public GitHub documents may carry only sanitized summaries.

## 2. Manual click-through script — complete on EACH device

Mark every case PASS / FAIL / BLOCKED and record steps, evidence and issue references.

| ID | Action | Expected observation |
|---|---|---|
| C01 | Open authenticated Draft 1154 Preview in a fresh tab and reload | College Search heading, labels and real-school results visible; no raw Divi shortcodes, HTML or JavaScript source printed to the page |
| C02 | Observe cold data loading (network throttling if available) | Visible loading feedback; inputs disabled until ready; no fallback records |
| C03 | Let loading complete | **6,243 schools found**, initial **24** visible cards, A–Z sort, no more than 24 cards in DOM |
| C04 | Search for Harvard University in mixed case and with surrounding whitespace | **1** matching school in Cambridge, MA; result name and correct website link, opens new tab |
| C05 | Keep Harvard search; choose NY | **0 schools found**; explanatory no-results message; Show more not shown |
| C06 | Press Clear | Search empty, state all, sort A–Z, **6,243** results restored; 24 cards; focus returns to name input |
| C07 | Choose only NY, then CA, then PR | Counts **417** (NY), **658** (CA), **138** (PR), with state-correct results |
| C08 | Clear and sort Z–A | Order reverses logically; the total remains 6,243; only 24 first-page cards rendered |
| C09 | Clear and choose Show 24 more | **24 to 48** visible cards, no extra dataset request |
| C10 | Search Enterprise State Community College | The school shows **School website not reported**, no fabricated URL |
| C11 | Open About this data, then close via Enter/Space | One collapsed-by-default section cites June 10, 2026 U.S. Department of Education College Scorecard data, 6,243 source institutions, coverage caveat |
| C12 | Use Tab / Shift+Tab / Enter across labels and links | Every interactive control named; skip link first, school-specific link names, visible focus, no keyboard trap |
| C13 | Rotate mobile device, test landscape, narrow width, text size and pinch zoom | No clipped controls, overflow, overlap; zoom remains enabled |
| C14 | Inspect Console and Network where supported | **zero unexpected console errors**, zero uncaught JS page errors; dataset HTTP 200, no CORS error |
| C15 | Block dataset request or go offline, then restore connection and press Retry | Visible failure without results or fallback; Retry restores all 6,243 schools. If mobile request blocking unavailable, mark BLOCKED on that device and provide desktop evidence. |

**Desktop-only extras:** use authenticated Chrome/Edge DevTools, check the actual 24-to-48 DOM card count and the network request count, test 200% text zoom, keyboard-only navigation and link destinations. Keep console clear of unexpected errors.

**Physical iOS Safari extras:** portrait and landscape, Safari pinch zoom, browser text size and VoiceOver where available; use Mac Safari remote Web Inspector to collect console/network errors if possible. If not available, label console inspection BLOCKED, not passed. Record iPhone model and iOS version.

**Physical Android Chrome extras:** portrait/landscape, pinch zoom, Android text-size adjustment, TalkBack where available; use Chrome USB remote DevTools if possible. If not available, label console inspection BLOCKED, not passed. Record Android model and browser version.

**Data caveat:** this is descriptive federal source data, not an admissions predictor or a complete independently certified inventory of accredited institutions. **732** website URLs are null in the source; do not invent links.

## 3. Device evidence and test-result ledger

| Environment | Tester/date, version, evidence | Overall result |
|---|---|---|
| Desktop Chrome/Edge, actual authenticated Draft 1154 | Unassigned; private evidence pending | **NOT RUN** |
| Physical iOS Safari, actual authenticated Draft 1154 | Unassigned; private evidence pending | **NOT RUN** |
| Physical Android Chrome, actual authenticated Draft 1154 | Unassigned; private evidence pending | **NOT RUN** |

For each device record C01–C15 outcomes, device and browser version, screenshots or private recordings, blocking issues, actual search/state counts, whether all links and focus were checked, console errors, tester name and sign-off date. Do not infer mobile PASS from Chrome emulation.

## 4. WordPress-host Lighthouse and publication gates

1. In authenticated **desktop Chrome**, open the real WordPress **Draft 1154** preview. Verify correct search results and Divi integration before measuring. An external Google PageSpeed Insights service cannot load private staging.
2. If authenticated DevTools Lighthouse can audit the Draft **without redirecting to login**, perform **three fresh Mobile Performance runs** with consistent settings. Preserve original reports privately. Do not make the page public just to run Lighthouse.
3. Record each actual-host LCP, compute **median**. Passing gate: median mobile LCP **<3,000 ms** and **zero unexpected console errors**. A result measuring a login page, 404, or local standalone proxy does NOT count. If authenticated staging Lighthouse is technically unavailable, record **BLOCKED — real WordPress host LCP unverified** and obtain an owner-approved alternative before any release.
4. Previously measured proxy figures **2,102.0 / 1,663.9 / 1,665.3 ms**, median **1,665.3 ms**, are from [GitHub Lighthouse proxy CI](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/38045619803), **NOT the WordPress staging host**. Never treat this static fixture as the actual-host production gate.

| Actual WordPress Draft measurement | Mobile LCP (ms) | Page identity verified | Result |
|---|---|---|---|
| Run 1 | Not measured | No | **NOT RUN** |
| Run 2 | Not measured | No | **NOT RUN** |
| Run 3 | Not measured | No | **NOT RUN** |
| **Median** | **UNVERIFIED** | Real WordPress Draft 1154 still unmeasured | **NOT PASSED** |

The device checks, real WordPress-host LCP gate, zero console errors, source-data integrity and **explicit owner approval** must all precede production release. A draft GitHub PR is not a production authorization.

## 5. Safe rollback — current staging and future incidents

**Known-safe pre-release state:** page **1154 Draft**; page **1044 Draft** (its previous NY20 evidence was intentionally withheld); parent resource page **452 unchanged**; GitHub history and national data shards preserved.

**If private staging is broken:**
1. STOP. Do not publish any page to debug a failure. Keep 1154 and 1044 Draft. Collect failure steps, device information, screenshot and console/network logs privately.
2. In [Draft 1154 editor](https://www.lauraelizabethhand.com/wp-admin/post.php?post=1154&action=edit), inspect saved Divi Code and WordPress revisions. Restore **only 1154** to a last independently reviewed and verified staging revision if needed; never restore old unreviewed NY20 content, delete national files, modify page 452, or expose Draft pages publicly.
3. For GitHub, make a normal **revert commit** on the Sprint 1 branch if the regression came from a new commit. **Do not force-push, reset, or rewrite Git history.** Re-run national integrity, component, a11y and performance CI, then authenticated preview checks.
4. Confirm again: **1154 Draft; 1044 Draft**. Record what changed and why. This is a procedure, not an instruction to execute rollback during Task 9.

**If a future explicitly approved production release breaks:**
1. Identify the exact released page and commit; preserve incident evidence and stop traffic promotion.
2. An authorized WordPress editor may return **only the affected College Search production page to Draft** as an emergency availability trade-off. **This operation is not authorized during Task 9.**
3. Restore an older production version **only if independently reviewed and explicitly owner-approved**; NEVER restore the unreviewed original NY20 explorer as fallback. If no safe reviewed version exists, keep the tool offline pending approval rather than serving misleading results.
4. Validate the affected URL is no longer serving broken data, purge affected page caches if required, and ask before changing other published pages, menus or redirects.
5. Document recovery, validation evidence and approval before republishing.

**Rollback executed? NO.** No publication, data deletion, modification to production 1044 or page 452, force-push, or history rewrite is part of Task 9.

## 6. Release record (intentionally pending)

- Runbook date: **2026-10-10**
- Authenticated WordPress Draft browser execution: **UNVERIFIED**
- Desktop manual device testing: **NOT RUN**
- Physical iOS Safari testing: **NOT RUN**
- Physical Android Chrome testing: **NOT RUN**
- WordPress-host median mobile LCP: **UNVERIFIED**
- Owner production publication authorization: **NOT GRANTED**
- **Sprint 1 Task 10 remains NEXT**, after this documentation is verified; Task 10 notification does not itself confer release approval.
