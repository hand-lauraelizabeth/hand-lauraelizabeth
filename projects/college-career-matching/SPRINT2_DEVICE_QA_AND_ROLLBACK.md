# Sprint 2 College Search — manual device QA and rollback plan

**Prepared 2026-10-10. TEST PLAN ONLY — NOT EXECUTED.** Technical QA documentation, not visitor-facing copy. Test **only authenticated WordPress Draft page 1154**. The published production page **1044** is the owner-approved **Sprint 1** test release and must remain unchanged. This plan authorizes no WordPress edits, publication, merge, or data deletion.

## Access and evidence
S2-08 saved the Draft 1154 Divi component and pinned external script/data. **Authenticated front-end execution remains BLOCKED/unverified.** An anonymous draft-preview 404 is expected. An authorized editor must open page 1154 in the WordPress editor, choose Preview in the same signed-in browser, and confirm it renders actual controls instead of raw Divi shortcodes. Do not publish the Draft to make it testable.

Run each case independently on **desktop Chrome/Edge**, **physical iOS Safari**, and **physical Android Chrome**. Simulated mobile Chromium checks do not replace real devices. Record device/OS/browser versions, orientation, date, tester, observed counts, result (PASS/FAIL/BLOCKED/NOT RUN), and a private evidence reference. Keep screenshots, preview links, browser sessions, request logs, and detailed traces in a private evidence location, not the public repository. Where DevTools are unavailable on mobile, mark network/console cases BLOCKED rather than PASS.

## Verified baseline
College Scorecard snapshot **2026-06-10**: **6,243** institutions keyed by UNITID. Missing source values: control **0**, locale **531**, undergraduate enrollment **781**; unknown stays **null**. Any selected non-All filter excludes unknown values in that field; All includes them. Undergraduate enrollment is not total enrollment. Exactly **three NEW Sprint 2 dropdowns**: Institution control (Public / Private nonprofit / Private for-profit), Campus setting (City / Suburb / Town / Rural), Undergraduate size (Under 5,000 / 5,000–14,999 / 15,000+). Retain Sprint 1 name, state, sort, result count, Clear, Show more, loading, error/Retry, and one source disclosure. The independently verified Public + City + Under 5,000 intersection is **306**.

## D01–D23 — repeat on every device

| ID | Action | Expected result |
|---|---|---|
| D01 | Open authenticated Draft 1154 preview and reload | Actual College Search renders in Divi, no raw source; 1154 remains Draft and 1044 remains published unchanged. |
| D02 | Cold load with throttling where possible | Loading indicator; disabled controls until verified data; no fallback schools. |
| D03 | Complete load and inspect network | 6,243 found, first 24 cards, A–Z; one pinned external script and one v2 data request, HTTP 200/CORS compatible. |
| D04 | Inspect and use every input | Existing School name, State or territory, Sort by; exactly three new active dropdowns. No inert controls. |
| D05 | Read missing-data summary | Denominator 6,243; unknown control 0, locale 531, undergraduate size 781; selection excludes null. |
| D06 | Select Public, Private nonprofit, Private for-profit separately | Counts/cards and active selections update; only matching controls remain. Clear between selections. |
| D07 | Select City, Suburb, Town, Rural separately | Each changes results; unknown locale excluded, never treated as rural. Clear between. |
| D08 | Select Under 5,000; 5,000–14,999; 15,000+ | Each changes results; unknown size excluded; band boundaries 4,999 / 5,000 / 14,999 / 15,000. |
| D09 | Select Public + City + Under 5,000, other filters All | Exactly 306 schools; all three active selections visible. |
| D10 | Add name search and NY state to D09 | Intersection uses AND; active summary and count reflect all five filters. |
| D11 | Enter impossible name with other filters selected | Zero schools, visible empty-state guidance, no cards or Show more; active filters remain. |
| D12 | Clear from zero results | All filters blank/All, sort A–Z, 6,243 found, 24 cards, name focused. |
| D13 | Sort Z–A alone, then Clear | Correct descending order and active sort label, unchanged total; Clear restores A–Z. |
| D14 | Click Show more twice | Cards 24 → 48 → 72, count updates, no new data fetch; Clear returns to 24. |
| D15 | Show 48 then change Campus setting to Rural | Pagination resets to first 24 matching cards; Clear restores 6,243/24. |
| D16 | Search Harvard University with mixed case/whitespace, then NY | Harvard Cambridge MA when unfiltered; NY contradiction yields zero. |
| D17 | Inspect a record with null website URL | Displays School website not reported; no invented link. |
| D18 | Open About this data and close by keyboard | Exactly one collapsed disclosure, source dated 2026-06-10, Enter/Space works. |
| D19 | Navigate by Tab/Shift+Tab, arrow keys, Enter/Space | Skip link, six labeled inputs, buttons and links have visible focus; no keyboard trap. |
| D20 | Test 200% zoom, portrait/landscape, text size, pinch zoom | No clipped controls, horizontal overflow, overlapping cards, or zoom restriction. |
| D21 | Check result count announcement and accessibility names | Live result count, descriptive unknown counts tied to selects, unique link names; VoiceOver/TalkBack where available. |
| D22 | Simulate invalid/offline v2 response, restore connection, activate Retry | Error alert; no stale/fallback cards; disabled controls; keyboard Retry restores 6,243. If device cannot intercept requests, mark BLOCKED. |
| D23 | Inspect console/network and recheck page status | Zero unexpected console/page errors, pinned external JS and v2 data HTTP 200; Draft 1154 unchanged, public 1044 unchanged. |

**Desktop:** capture DOM card counts, network request count, keyboard focus, and 200% zoom in authenticated DevTools. **Physical iOS Safari:** portrait/landscape, pinch zoom, Safari text sizing, VoiceOver where available, remote Web Inspector when possible. **Physical Android Chrome:** portrait/landscape, pinch zoom, font/display scaling, TalkBack where available, remote Chrome DevTools when possible.

## Execution ledger — no manual device passes claimed
| Environment | Evidence | Status |
|---|---|---|
| Desktop Chrome/Edge, authenticated Draft 1154 | No authenticated preview execution yet | **BLOCKED** |
| Physical iOS Safari, authenticated Draft 1154 | No physical-device evidence | **NOT RUN** |
| Physical Android Chrome, authenticated Draft 1154 | No physical-device evidence | **NOT RUN** |

Record each D01–D23 result per device, observed counts for D03/D05/D09, errors for D22/D23, and any issue references. A CI pass is not a physical-device pass.

## Evidence, release gate, rollback
[S2-06 accessibility CI](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/38053005162) passed simulated 1440/390/320px Chromium keyboard, labels, zoom, zero-result and Retry checks. [S2-07 mobile Lighthouse CI](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/38053297837) measured LCP **867.7 / 1,672.5 / 1,671.9 ms**, median **1,671.9 ms** against a **local static proxy**, not WordPress. [S2-08 CDN preflight](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/38054940387) verified pinned external JS and v2 JSON but **not** authenticated Divi execution.

**Outstanding gates:** authenticated Draft 1154 runtime and console/network, physical desktop/iOS/Android testing, three independent actual WordPress-host mobile Lighthouse runs with median LCP **<3,000 ms**, and **fresh explicit owner approval** for any Sprint 2 production release. No WordPress-host LCP or physical-device result is claimed.

**Safe rollback plan only:** Keep 1154 Draft if broken; collect private diagnostics. An authorized editor may inspect its revisions and request approval before restoring a reviewed Draft-only version. GitHub regression recovery requires a normal reviewed revert, never force-push or deletion. Do not edit production 1044 or parent 452. **No rollback executed.**

**Queue:** S2-09 documents manual QA only. **S2-08 authenticated-preview blocker remains open.** Next queued S2-10 drafts visitor-facing progress notes without publishing; S3-01 remains blocked until owner review.
