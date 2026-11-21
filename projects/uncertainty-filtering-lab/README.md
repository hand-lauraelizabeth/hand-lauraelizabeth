# Unknown Is Not No — Filtering Lab

A standalone exercise about the difference between **confirmed**, **unknown**, and **verified not offered** in college-program discovery. The five institutions and all records are fictional. This exercise does not report current offerings, admissions requirements, or eligibility for any real college.

## Try the exercise

Open [index.html](./index.html) in a modern browser. No build, account, installation, or network connection is required. Choose an evidence-state filter, narrow by credential, and compare which records remain. Try **Confirmed and unknown** to retain programs whose current availability has not been established. Use **Reset filters** to restore all five records. Then answer the applied capstone and reveal the four-part self-assessment rubric.

## Interpreting the evidence

- **Confirmed:** the fictional fixture includes a dated current catalog record for the specified credential.
- **Unknown:** the fixture lacks sufficient dated, campus-specific evidence; this is not a negative finding.
- **Verified not offered:** the fictional fixture explicitly excludes the credential at the specified campus. The conclusion applies only to that invented fixture.
- Historical completions do not establish that a program is currently offered. Institution-wide figures do not establish program-specific admissions policies.

In a real-world workflow, preserve the source URL, publication or retrieval date, campus identity, credential, and unresolved questions. Recheck official institution sources before making consequential decisions. The exercise deliberately does not connect to live Scorecard, IPEDS, or institutional data.

## Local-only behavior

The HTML contains a fixed five-record fixture. Filtering and rubric reveal run entirely in the browser. The free-text capstone is not sent to a server or stored; refreshing clears it. The page has no third-party scripts, analytics, or export mechanism.

## Focused acceptance checklist (not a test report)

1. Open locally; verify five fictional records appear and the summary reads **5 of 5**.
2. Set **Confirmed only**; expect two records. Select **Certificate**; expect one.
3. Set **Confirmed and unknown** and **Bachelor's**; expect two records, including the unknown Elm City record. The verified-negative Pine Valley record must not appear in this evidence state.
4. Set **Confirmed only** and **Certificate**; verify the one-record state. Confirm **Reset filters** restores five records and moves focus to the evidence-state select.
5. Enter a capstone response, reveal the rubric, and confirm the response remains editable; refresh and confirm the response is cleared.
6. Check Tab/Shift+Tab, visible focus, screen-reader status announcements, and 320px reflow without horizontal clipping. Verify no requests containing capstone text are made.

These are proposed checks, **not claims of completed browser, device, or assistive-technology testing**. The page is a review candidate, not a production release.

## Release boundaries

Keep this exercise distinct from the live College + Career Matcher and from empirical program evidence. Do not replace missing source fields with guessed values. Publication, merging, or embedding on the public website requires item-specific approval and relevant acceptance evidence.
