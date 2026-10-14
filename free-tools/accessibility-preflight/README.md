# HTML Accessibility Preflight

A free browser-local tool for preliminary HTML checks. Paste HTML or open a local .html/.htm file (2 MB maximum). The tool reports selected heading, image, form, link, table, language, title, and duplicate-ID concerns and exports a review report as JSON or spreadsheet-precaution CSV.

This is **not a WCAG conformance evaluation or accessibility certification**. Automated markup checks cannot judge alternative-text meaning, contrast, keyboard usability, reading order, runtime interactions, or screen-reader experience. Findings use element tags/IDs as approximate locations, not original source line numbers. The HTML is parsed without running its scripts. Files are not uploaded, and the interface has a restrictive CSP. Do not use sensitive documents on shared computers.

For a local preview, serve this folder using a static web server. Run `python smoke.test.py` with Playwright and Chromium installed; this smoke test injects the source because direct HTTP navigation is restricted in the test environment, so it does not verify served CSP or screen-reader behavior.

Official guidance reviewed October 14, 2026:
- [W3C WAI Easy Checks](https://www.w3.org/WAI/test-evaluate/preliminary/)
- [W3C WCAG 2.2 Understanding](https://www.w3.org/WAI/WCAG22/Understanding/)
- [W3C Non-text Content 1.1.1](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html)
