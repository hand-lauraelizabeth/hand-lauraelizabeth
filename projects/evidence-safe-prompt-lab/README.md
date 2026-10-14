# Evidence-Safe Prompt Lab

A self-contained browser demonstration for composing evidence-conscious prompts **and** documenting reviewer-assigned source-to-claim support records.

## Try it

Download this folder and open [index.html](index.html) in a modern browser. GitHub previews the HTML source instead of running it. No server, model, paid API, or account is required.

## What works

- Choose drafting, support-checking, citation audit, counterevidence review, or teaching-feedback mode.
- Enter a goal, context, approved evidence boundary and desired output.
- Toggle evidence, uncertainty, support-classification, counterevidence, citation-integrity and privacy constraints.
- Add any number of **human-reviewed** claim records with source ID, specific excerpt, support class (**DIRECT**, **PARTIAL**, **CONTRADICTED**, **NOT ESTABLISHED**), rationale and counterevidence/verification need. Remove records as needed.
- Generate and copy a structured prompt that includes the evidence contract and reviewed records.
- Export the records as a local JSON file for transparent follow-up.

## Important limitations

**Support classifications are entered by the user, not calculated or verified by this page.** The tool does not retrieve sources, authenticate citations, run a language model, determine truth, or validate whether a claim follows from a passage. A DIRECT, PARTIAL or CONTRADICTED entry requires a source identifier and excerpt, but the page cannot verify their accuracy. Include only appropriately authorized source material.

**Privacy:** Client-side processing, no external requests, analytics or persistent storage. JSON export is explicitly user-initiated; the page does not sync or store it.

Use the [Prompt Literacy Debugger](../prompt-literacy-debugger/) for reviewing a prior prompt and the [Ethical AI Scenario Auditor](../ethical-ai-scenario-auditor/) for operational risk planning.
