# Prompt Literacy Debugger

A self-contained browser demonstration that helps learners inspect an existing prompt across seven dimensions: task, audience/context, evidence boundaries, authority limits, output requirements, verification, and human responsibility.

## Try it

Download this folder and open [index.html](index.html) in a modern browser. GitHub's file view displays the source code; it does not run the interactive page. No server, account, paid model or API key is needed.

## What works

- Paste or type a prompt, choose use-case, consequence and data-sensitivity context.
- **Suggest ratings (review required)** scans for limited textual clues, assigning provisional **partial** or **missing** ratings; it **never** declares a dimension explicitly satisfied. Word matches are fallible and do not establish adequacy.
- Review all seven ratings yourself, including **explicit**, **partial / implied**, **missing**, or **not rated**.
- Generate a coverage map and a rebuild scaffold that explicitly carries forward all unresolved dimensions.
- Receive human-review, privacy and escalation reminders for higher-consequence or sensitive uses.
- Copy the resulting scaffold locally, or clear the assessment.

## Limitations and classroom use

This tool does **not** use AI, infer the meaning of a prompt reliably, judge legal compliance, or validate external evidence. Clues are simple regular-expression matches; user review is mandatory. Compare different students' ratings to make hidden assumptions visible, then test revisions with approved systems.

For source-to-claim **composition**, use the [Evidence-Safe Prompt Lab](../evidence-safe-prompt-lab/). For workflow risk and oversight planning, use the [Ethical AI Scenario Auditor](../ethical-ai-scenario-auditor/).

**Privacy:** The page has no network requests, analytics or persistent browser storage. Do not paste sensitive or restricted information into an unapproved environment even when the local page does not upload it.

**Framework context:** This independently developed teaching demo draws on ideas of human agency, critical evaluation and risk management in the [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) and [UNESCO AI Competency Frameworks](https://www.unesco.org/en/digital-education/ai-future-learning/competency-frameworks). It is not an official assessment or certification.
