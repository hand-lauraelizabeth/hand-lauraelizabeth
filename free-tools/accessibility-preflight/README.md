# HTML Accessibility Preflight

A free browser-local tool for preliminary HTML checks. Paste HTML or open a local .html/.htm file (2 MB maximum). The tool reports selected heading, image, form, link, table, language, title, and duplicate-ID concerns and exports a review report as JSON or spreadsheet-precaution CSV.

This is **not a WCAG conformance evaluation or accessibility certification**. Automated markup checks cannot judge alternative-text meaning, contrast, keyboard usability, reading order, runtime interactions, or screen-reader experience. Findings use element tags/IDs as approximate locations, not original source line numbers. The HTML is parsed without running its scripts. Files are not uploaded, and the interface has a restrictive CSP. Do not use sensitive documents on shared computers.

For a local preview, serve this folder using a static web server. Run `python smoke.test.py` with Playwright and Chromium installed; this smoke test injects the source because direct HTTP navigation is restricted in the test environment, so it does not verify served CSP or screen-reader behavior.

Official guidance reviewed October 14, 2026:
- [W3C WAI Easy Checks](https://www.w3.org/WAI/test-evaluate/preliminary/)
- [W3C WCAG 2.2 Understanding](https://www.w3.org/WAI/WCAG22/Understanding/)
- [W3C Non-text Content 1.1.1](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html)

## Relationship and accessible-name preflight

The HTML preflight now flags unresolved, empty, or repeated ARIA ID references; labels pointing to missing or unsupported controls; table-header references that do not resolve within the same table; missing iframe titles; and a narrow visible-text versus explicit `aria-label` mismatch. These are **review prompts**, not automatic WCAG failures. Hidden referenced labels may be valid; dynamic applications can establish relationships after load; computed accessible names, CSS visibility, and screen-reader announcements still require manual testing. Source IDs are matched case-sensitively and are not normalized. The checker also reviews `aria-flowto` alternate-reading-order references and flags multiple targets in single-ID `aria-details` and `aria-errormessage` attributes; multi-target `aria-describedby` remains valid. These checks do not verify that alternate reading order works in assistive technology.

Run `python relationship.smoke.test.py` for the committed 12-case synthetic Chromium suite. It injects the module into a browser DOM and does **not** verify a deployed site's CSP or assistive-technology behavior.

Additional official references (reviewed October 14, 2026):
- [W3C WAI-ARIA 1.2, ID reference error processing](https://www.w3.org/TR/wai-aria-1.2/)
- [W3C WAI accessible names and descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/)
- [W3C WCAG 2.2, Label in Name](https://www.w3.org/WAI/WCAG22/Understanding/label-in-name)

The checker also reports when two different elements explicitly own the same uniquely resolved target through `aria-owns`, or when an element owns itself. Duplicate IDs, unresolved targets and repeated tokens retain their separate findings. These are static review prompts; complex ownership cycles and assistive-technology behavior still require manual review. Source: [WAI-ARIA 1.2, `aria-owns`](https://www.w3.org/TR/wai-aria-1.2/#aria-owns) (reviewed October 31, 2026).
