# Reverse ATS · Role Evidence Studio

An interactive, evidence-centered career decision workspace. It helps people explore plausible role families, interpret job requirements, distinguish experience from what an application currently makes visible, and decide what to document, verify, or develop next.

**[Use the interactive website tool](https://www.lauraelizabethhand.com/resources/career-professional-development-tools/reverse-ats/)**

[Read the design and evidence method](ROLE_EVIDENCE_METHOD.md) for the reasoning behind requirement mapping, verification, confidentiality, and claim-strength controls.

## Two active workspaces

### Role Evidence Analysis
- Paste a job description and candidate evidence, optionally separated by source markers: `[resume]`, `[portfolio]`, `[public]`, `[document]`, or `[user]`.
- Classify required qualifications, preferred signals, responsibilities, tools, context, seniority, and scope.
- Inspect requirement-by-requirement visibility, source provenance, human-reviewed support, and gap explanations.
- Detect chronology and scope cues without turning them into verified claims.
- Keep elapsed-experience requirements unresolved when only calendar-year coverage is available, including decimal, range, and written-number requirements.
- Review evidence nodes, record source references, note confidential material, and set verification status.
- Export a requirement matrix (CSV) and appropriately filtered evidence graph (JSON).

### Career Discovery & Tracking
- Supply résumé/CV material, digital-footprint details, supporting documents, and contextual information.
- Parse supported text, DOCX, PDF, HTML, JSON, CSV, and other browser-readable formats.
- Explore role-family suggestions with source-weighted skills and seniority heuristics.
- Filter roles by geography, estimated pay, visible match, status, and sorting preference.
- Track application states and notes in browser storage; export CSV/JSON.
- Optionally add public GitHub repository descriptions.

These workspaces remain independently usable. A shared candidate profile now supports explicit browser-local save/load and private JSON transfer between them without clearing the discovery tracker. Transfers from Role Evidence Analysis exclude nodes labeled private, anonymize-only, or do-not-use. Imported verification labels still require human review; exported JSON can contain personal material and should not be published.

## How to start

For a specific opportunity, open **Role Evidence Analysis**, use the sample job and fictional sample candidate to explore the workflow, or paste your own job and experience. Read the requirement matrix and evidence-review panel before drawing conclusions.

For a guided first visit, use the [10-minute fictional worked example](WORKED_EXAMPLE.md) to inspect a duration requirement, distinguish coordination from authority, and produce an evidence-recovery plan.

To discover possible directions from your experience and record opportunities, expand **Career Discovery & Tracking**. Build a profile from materials, adjust the filters, and export the tracker when needed.

## Transferring evidence between workspaces

Use **Save profile locally** and **Load saved profile** when the workspaces share the same browser origin and storage context. When website embeds or browsers have separate storage, choose **Download profile JSON** in one workspace and **Import shared profile JSON** in the other. In the discovery tracker, imports merge source text instead of wiping existing source fields, and they do not modify application statuses or notes. Save again when you want to update the transferable snapshot.

## Interpretation and privacy

Outputs are diagnostic guidance that requires human judgment. A missing term can indicate missing capability, unexpressed experience, weak public proof, an unclear date, or a claim that still needs verification. Source corroboration, authority, chronology, and confidentiality matter.

Input text and files are handled in the browser by default. The discovery tracker uses browser-local storage; exports are user-initiated. Optional public-profile lookups involve a network request when selected. Salary estimates without a cited posting range are heuristic, not offers or verified market quotes.

## Source files

- [`index.html`](./index.html): posting analysis and structured evidence review
- [`career-discovery-tracker.html`](./career-discovery-tracker.html): role discovery, document input, and local pipeline tracking
- [`evidence-graph.schema.json`](./evidence-graph.schema.json): evidence graph structure

The website implementation keeps the two applications isolated within the site's layout, so each can evolve without losing the other application's functionality.

## Release 2.6 — October 30, 2026

The analysis workspace now distinguishes covered calendar years from elapsed experience. A year-only chronology cannot satisfy a duration requirement, even when the underlying evidence node has been reviewed. The shared profile format and discovery tracker are unchanged.

- Deterministic chronology regressions: `node projects/reverse-ats-role-evidence-engine/tests/chronology.test.mjs`.
- HTTP-served Chromium integration: `python projects/reverse-ats-role-evidence-engine/tests/browser_scenarios.py` (Selenium and Chrome required).
- CI: [Role Evidence Studio validation](../../.github/workflows/role-evidence-validation.yml).

These checks cover the standalone application and its local embedding contract. They do not establish hiring outcomes, screen-reader compatibility, native browser zoom, or every surrounding WordPress interaction.
