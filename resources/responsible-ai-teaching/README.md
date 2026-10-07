# Prompt Literacy & Responsible AI Teaching Kit

A reusable teaching sequence for moving learners from “prompt tricks” toward evidence-aware, human-centered AI use.

The kit combines three browser-based demonstrations:

- [Prompt Literacy Debugger](../../projects/prompt-literacy-debugger/) — diagnose whether a prompt makes the task, evidence, limits, verification, and human responsibility explicit.
- [Evidence-Safe Prompt Lab](../../projects/evidence-safe-prompt-lab/) — build source-conscious prompts with support classifications, uncertainty, counterevidence, and citation guardrails.
- [Ethical AI Scenario Auditor](../../projects/ethical-ai-scenario-auditor/) — move from abstract principles to concrete workflow risks, mitigations, owners, oversight, and contestability.

All three tools run client-side and do not call an AI API.

Supporting teaching resources:

- [Responsible AI Scenario Bank](Scenario_Bank.md) — eight scenarios spanning low-stakes drafting, research, analytics, student support, hiring, education, health, and policy.
- [AI Literacy & Responsible Use Assessment Rubric](AI_Literacy_Assessment_Rubric.md) — nine-dimension rubric focused on task choice, evidence, verification, privacy, risk, human responsibility, provenance, and redesign.

## Teaching model

The sequence uses six moves:

**1. Decide → 2. Specify → 3. Ground → 4. Verify → 5. Assess impact → 6. Redesign**

This keeps prompting in context. A strong prompt does not make an unsuitable task appropriate for AI, and a polished output does not remove the need for evidence, verification, or accountable human judgment.

## Learning objectives

By the end of the sequence, learners should be able to:

1. Decide when AI is useful, when additional safeguards are required, and when a non-AI process is preferable.
2. Define a prompt as a task specification rather than a magic phrase.
3. Make audience, evidence boundaries, guardrails, output requirements, verification, and human responsibility explicit.
4. Distinguish source facts, inference, uncertainty, and unsupported claims.
5. Test whether evidence directly supports, partially supports, contradicts, or fails to establish a claim.
6. Identify privacy, bias, transparency, security, provenance, accountability, and contestability risks in an AI-assisted workflow.
7. Redesign the workflow so human judgment, documentation, verification, and monitoring are built into the process.
8. Explain why fluency, confidence, or a citation-shaped answer is not itself evidence of accuracy.

## Module 1 — Decide whether AI belongs in the task

Before optimizing a prompt, ask:

- What problem are we trying to solve?
- Who could be affected if the output is wrong?
- Does the task involve confidential, identifying, restricted, or otherwise sensitive information?
- Is AI making a decision, recommending one, summarizing evidence, drafting, or merely assisting with a reversible task?
- What must remain a human judgment?
- Is there a reasonable non-AI alternative?
- What would make us stop or change the approach?

### Teaching move

Give learners three tasks that look superficially similar but carry different stakes: drafting a low-stakes announcement, summarizing advising notes, and recommending an eligibility decision.

Ask them to identify what changes before they write a single prompt.

The point is that **AI literacy starts with task choice, not prompt wording**.

## Module 2 — Prompt literacy: make hidden assumptions visible

Use the [Prompt Literacy Debugger](../../projects/prompt-literacy-debugger/) to inspect seven dimensions:

| Dimension | Question |
| --- | --- |
| Task | What must actually be done? |
| Context | Who is the output for, and why is it needed? |
| Evidence | What information may support factual claims? |
| Boundaries | What must not be inferred, invented, disclosed, or decided? |
| Output | What form will make the response usable? |
| Verification | What needs to be checked, and how? |
| Human responsibility | Where does human judgment remain necessary? |

### Activity

Give every learner the same vague prompt. Have them rate the seven dimensions independently.

Compare disagreements before rebuilding the prompt.

The instructional value is not the score. It is the disagreement: learners discover which assumptions they thought were obvious but never stated.

## Module 3 — Evidence contracts and source-to-claim support

Use the [Evidence-Safe Prompt Lab](../../projects/evidence-safe-prompt-lab/) to make evidence constraints visible.

Support labels:

- **DIRECT** — the source explicitly establishes the material claim.
- **PARTIAL** — the source supports part of the claim or supports a narrower formulation.
- **CONTRADICTED** — the source conflicts with the claim.
- **NOT ESTABLISHED** — the supplied evidence does not justify the claim.

### Evidence ladder exercise

For each material sentence in an AI-assisted draft:

1. Identify the factual claim.
2. Point to the source evidence that bears on it.
3. Assign a support label.
4. Rewrite the sentence so confidence matches the evidence.
5. State what additional evidence could change the classification.

This turns “fact checking” into a visible reasoning process rather than a final cosmetic pass.

## Module 4 — Verification, citation integrity, and provenance

Teach four non-negotiable behaviors:

1. Do not invent authors, titles, dates, quotations, page numbers, URLs, DOIs, statistics, or source details.
2. Keep a traceable boundary between source material, user-supplied context, model inference, and new research.
3. Treat citations as pointers to evidence, not decorations that make prose look scholarly.
4. Preserve disagreement, missingness, ambiguity, and uncertainty when they are material.

### Mini-assessment

Provide one supported claim, one partially supported claim, and one unsupported claim. Ask learners to produce:

- the support classification;
- a two-sentence justification;
- a corrected version of the claim;
- a verification note.

Grade evidence alignment rather than prose polish.

## Module 5 — Ethical AI is workflow design

Use the [Ethical AI Scenario Auditor](../../projects/ethical-ai-scenario-auditor/) to move beyond principle lists.

Review:

- purpose and necessity;
- data minimization;
- notice and consent;
- bias and differential impact;
- transparency;
- human oversight;
- contestability;
- security;
- provenance;
- uncertainty and limits;
- monitoring;
- affected-community perspective.

### Role-based activity

Give groups the same scenario but different perspectives:

- person affected by the system;
- program owner;
- data steward;
- security/privacy lead;
- instructor or practitioner;
- executive sponsor.

Each group identifies its three highest-priority risks, one design change, and the evidence that would show the change works.

Compare what became visible only when the perspective changed.

## Module 6 — Red-team and redesign the workflow

Ask learners to test plausible failure paths:

- What if the input is wrong, incomplete, adversarial, or out of date?
- What if a user trusts the output too much?
- What if performance differs across populations or contexts?
- What if the model or vendor changes?
- What if the record of how a decision was produced is lost?
- What if an affected person needs to correct data or challenge the result?
- What if the safest answer is to use a non-AI process?

The goal is not to “break the model” for sport. It is to discover where the surrounding process needs stronger controls.

## Applied capstone

### Scenario

A team proposes an AI assistant that summarizes intake notes and recommends follow-up resources.

### Deliverables

1. A purpose statement and explicit non-goals.
2. A decision on whether AI is appropriate for each step.
3. A data-minimization plan.
4. A diagnosed and rebuilt prompt.
5. An evidence-safe prompt.
6. A risk/mitigation table with owners and evidence.
7. A human-review and contestability pathway.
8. A provenance/logging plan.
9. A small pilot and evaluation design.
10. A go / revise / do-not-deploy-yet recommendation with conditions.

### Evaluation rubric

| Dimension | Strong evidence |
| --- | --- |
| Task choice | AI is used only where it adds value and the role of non-AI alternatives is considered. |
| Task design | Purpose, audience, constraints, and non-goals are explicit. |
| Evidence use | Claims are traceable; unsupported claims are narrowed or flagged. |
| Verification | Important facts, calculations, citations, and conclusions have an explicit checking method. |
| Risk reasoning | Risks are scenario-specific rather than copied from a generic list. |
| Mitigation quality | Controls change the workflow and have owners and evidence. |
| Human oversight | Review is meaningful, timely, and empowered to change outcomes. |
| Contestability | Affected people can correct information or reach an accountable human. |
| Provenance | Material sources, instructions, versions, and decisions can be traced. |
| Evaluation | Success and harm indicators are measurable and revisited after launch. |

## Instructor notes

- Avoid grading students on prompt length.
- Reward explicit uncertainty and appropriate refusal to overclaim.
- Teach minimization before optimization when sensitive or identifying data is involved.
- Use low-stakes examples before health, education, employment, public-benefit, or other consequential scenarios.
- Require learners to state what the tool cannot establish.
- Distinguish a model limitation from a workflow limitation.
- Treat ethical review as iterative: discovery, design, pilot, launch, and monitoring can surface different risks.
- Do not let a checklist score substitute for professional, legal, disciplinary, or affected-community review.

## Framework alignment

The kit is independently designed, but its emphasis on human agency, critical evaluation, risk management, and responsible use is consistent with:

- NIST, *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile* (NIST AI 600-1): https://doi.org/10.6028/NIST.AI.600-1
- UNESCO, *AI Competency Framework for Teachers* (2024): https://www.unesco.org/en/articles/ai-competency-framework-teachers
- UNESCO, *AI Competency Framework for Students* (2024): https://www.unesco.org/en/articles/ai-competency-framework-students
- OECD / European Commission, *Empowering Learners for the Age of AI: An AI Literacy Framework for Primary and Secondary Education* (2026): https://doi.org/10.1787/65cd27d4-en
- OECD AI Principles: https://www.oecd.org/en/topics/ai-principles.html

These sources inform the educational framing. The kit is not an official implementation, certification, legal assessment, or compliance instrument for any of them.

## Portfolio / professional use

The kit demonstrates curriculum architecture, AI literacy, responsible-AI judgment, prompt design, evidence synthesis, assessment design, technical teaching, and interactive learning design. It can be adapted for higher education, faculty development, workforce training, professional learning, or internal AI-governance education.
