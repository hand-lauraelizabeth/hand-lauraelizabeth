# Ethical AI Scenario Auditor

A self-contained browser-based teaching and planning demonstration that turns responsible-AI design questions into an **editable risk register**.

## Try it

Download this folder and open [index.html](index.html) in a modern browser. GitHub's file preview displays source, not a working app. The tool requires no account, server or AI API.

## What works

- Describe a proposed AI workflow, its potential consequences, and project stage.
- Review 12 areas: purpose; data minimization; notice; bias; transparency; oversight; contestability; security; provenance; uncertainty; monitoring; and affected-community participation.
- See separate counts of reported **yes**, **partial/unknown**, **no/unaddressed**, and **unanswered** questions, with no misleading 0–100 safety score.
- Create an editable entry for each unresolved question, including **risk**, **proposed mitigation**, **accountable owner**, **evidence/test**, **human oversight and contestability path**, and **implementation status**.
- Update a reusable review prompt from your risk edits, copy it, and export the register locally as JSON.
- Load an illustrative university advising scenario, or clear and begin again.

## Important limitations

The tool drafts domain-specific *starting points* for risks and controls, not independently verified findings. A reported Yes is unverified; suggested mitigations, owners and status labels require review. It cannot determine whether a workflow is ethical, safe, effective, legally compliant, or ready to deploy. For consequential use, seek independent domain and affected-community input, monitor outcomes and preserve a non-AI escalation route.

**Privacy:** Runs locally in the browser with no external API requests, analytics or persistent storage. Do not paste confidential or identifying records. Export is initiated by the user.

Related tools: [Prompt Literacy Debugger](../prompt-literacy-debugger/) and [Evidence-Safe Prompt Lab](../evidence-safe-prompt-lab/).
