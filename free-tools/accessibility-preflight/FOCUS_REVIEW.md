# Focus review for HTML Accessibility Preflight

Open `focus-preview.html` through a local static server to inspect pasted HTML or a local HTML file. The browser-only review adds potential keyboard-focus findings for controls inside `aria-hidden="true"` subtrees while preserving the original preflight's other checks and JSON/CSV exports. Input is parsed as HTML without running its scripts; no account or remote upload is required.

**Review prompts, not WCAG findings or certification.** Static HTML cannot establish computed CSS, scripted focus changes, flat-tree focusability, or screen-reader output. The check skips obvious disabled, inert, hidden, and inline CSS-hidden cases. Manually test keyboard and assistive technology before relying on results.

Run `python focus.smoke.test.py` for the committed synthetic Chromium checks. Browser-served CSP, Firefox/WebKit, native zoom, and assistive-technology behavior remain unverified.

Official source reviewed October 14, 2026: [W3C ACT rule 6cfa84](https://www.w3.org/WAI/standards-guidelines/act/rules/6cfa84/).
