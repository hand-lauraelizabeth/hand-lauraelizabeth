# Document reference preflight

The **Reference and Focus Review** preview adds static checks for same-document `#fragment` links, explicit form ownership (`form="id"`), and datalist associations (`list="id"`) alongside existing HTML, ARIA and hidden-focus checks. It preserves exact, case-sensitive identifiers and reports unresolved references as **review prompts**.

Run `python reference.browser.test.py` for synthetic browser cases, or `python reference.integration.test.py` for an injected-source interface check. No file is uploaded by the tool. The interface does not execute scripts from inspected HTML.

**Limits:** Dynamic scripts may add targets after load. External routes and cross-page fragments are not checked. Duplicate IDs, computed accessible names, actual keyboard operation, assistive-technology output, native zoom and served Content Security Policy require separate verification. These checks do **not** establish WCAG conformance.

Official sources reviewed October 14, 2026:
- [WHATWG HTML — fragment navigation](https://html.spec.whatwg.org/multipage/browsing-the-web.html#scroll-to-fragid)
- [WHATWG HTML — form-associated elements](https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#attr-fae-form)
- [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/)
