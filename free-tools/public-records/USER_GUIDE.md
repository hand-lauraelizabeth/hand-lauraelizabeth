# Use the Public Records Request Workspace

This free tool runs in your browser without an account. Open `index.html` through a local static server so its JavaScript modules load correctly. For example, from this folder run `python -m http.server 8765` and visit `http://localhost:8765/`. Do not publish personal request records to a public repository.

## Keep a usable record

1. Add a request with your own exact identifier, the agency or office, jurisdiction, description, and any known submission date or tracking ID. An unknown date can remain blank.
2. Add dated events linked to that request. Enter an exact source identifier for each email, letter, or other document when available. Keep the underlying source files separately; the tool does not attach or upload them.
3. Review the chronology and missing-documentation prompts. A missing flag is a reminder to check your records, **not** a finding about an agency's compliance.
4. Select **Download JSON** before closing the tab. The workspace is held in tab memory and is not automatically saved.
5. To reopen, use **Saved workspace JSON file** in a fresh, empty workspace. The import is rejected if requests or events already exist, so existing work cannot be overwritten silently.

The JSON export preserves exact request and source ID strings, including spaces. Imports accept only the tool's versioned JSON schema, valid UTF-8, and files of at most **5,000,000 bytes**. Unsupported versions, unknown fields, duplicate IDs, broken references, and invalid dates are rejected. Never assume an imported file is safe merely because it ends in `.json`.

**Download CSV** is for spreadsheet review, not for reopening. It applies a precaution to formula-like cell values, which changes those exported values and does not guarantee safety in every spreadsheet application. Keep the JSON backup as the authoritative exact-string copy.

## Privacy and limits

Records remain in the current browser tab; this tool does not send them to an agency or remote server. Do not use shared computers for sensitive records. It does not calculate legal deadlines, determine eligibility, provide legal advice, or replace agency instructions. Federal FOIA procedures differ from state and local public-records laws.

For federal requests, consult [FOIA.gov](https://www.foia.gov/how-to.html), the [U.S. Department of Justice FOIA Reference Guide](https://www.justice.gov/oip/department-justice-freedom-information-act-reference-guide), and [National Archives FOIA guidance](https://www.archives.gov/foia/foia-guide).

## Accessibility and testing limits

Inputs have visible labels and status updates use a live region. Synthetic Chromium tests exercise import, export, mobile width, enlarged text, and safe display of HTML-like strings. Those checks do **not** establish WCAG conformance. Browser-served CSP, native zoom, screen readers, Firefox, and WebKit still require independent review.
