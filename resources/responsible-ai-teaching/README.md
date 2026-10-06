# Prompting & Ethical AI Teaching Kit

A reusable teaching sequence for moving learners from “prompt tricks” to evidence-aware, ethically reasoned AI use.

This kit grows out of Laura Elizabeth Hand’s archived prompt-development and source-verification work, including iterative source-to-claim checks used while researching AI, healthcare, cybersecurity, and evidence synthesis. It pairs those practices with two browser-based demonstrations in this repository:

- [Evidence-Safe Prompt Lab](../../projects/evidence-safe-prompt-lab/)
- [Ethical AI Scenario Auditor](../../projects/ethical-ai-scenario-auditor/)

## Learning objectives

By the end of the sequence, learners should be able to:

1. Define a prompt as a task specification with an explicit evidence contract rather than a magic phrase.
2. Distinguish source facts, inference, uncertainty, and unsupported claims.
3. Test whether evidence directly supports, partially supports, contradicts, or fails to establish a claim.
4. Identify when AI use creates privacy, bias, transparency, security, provenance, or accountability risks.
5. Redesign an AI-assisted workflow so human judgment, contestability, documentation, and verification are built into the process.
6. Explain why a fluent output is not itself evidence of accuracy or responsible use.

## Module 1 — Prompt architecture: make the contract visible

Teach prompts as six components:

| Component | Question |
| --- | --- |
| Role | What kind of reasoning perspective is useful? |
| Task | What must be done? |
| Context | What does the system need to understand? |
| Evidence boundary | Which sources may support factual claims? |
| Guardrails | What must it not infer, invent, disclose, or overstate? |
| Output contract | What structure will make the reasoning inspectable? |

### Activity

Give learners a vague request such as “summarize this source and tell me whether my argument is right.” Have them run the task once with the vague request and once with the Evidence-Safe Prompt Lab.

Compare:
- unsupported specificity;
- whether source facts and inference are separated;
- whether the output notices missing evidence;
- whether citations or quotations are invented;
- whether the conclusion is stronger than the source.

The lesson is not that longer prompts are automatically better. The lesson is that important constraints should be explicit.

## Module 2 — Claim-to-source support

Use the support labels:

- **DIRECT** — the source explicitly establishes the material claim.
- **PARTIAL** — the source supports part of the claim or supports a narrower formulation.
- **CONTRADICTED** — the source conflicts with the claim.
- **NOT ESTABLISHED** — the supplied evidence does not justify the claim.

### Evidence ladder exercise

For each sentence in an AI-assisted draft:

1. Underline the material factual claim.
2. Point to the exact source evidence that bears on it.
3. Assign one support label.
4. Rewrite the sentence so its confidence matches the evidence.
5. List what additional evidence would change the classification.

This turns “fact checking” into a visible reasoning process rather than a final cosmetic pass.

## Module 3 — Citation integrity and provenance

Teach four non-negotiable behaviors:

1. Do not invent authors, titles, dates, quotations, page numbers, URLs, DOIs, or publication details.
2. Keep a traceable boundary between source text, user-supplied context, model inference, and new research.
3. Treat a citation as a pointer to evidence, not a decoration that makes prose look scholarly.
4. Preserve disagreement, missingness, and ambiguity when they are material to the conclusion.

### Mini-assessment

Provide one supported claim, one partially supported claim, and one unsupported claim. Ask learners to produce:
- the support classification;
- a two-sentence justification;
- a corrected version of the claim;
- a verification note.

Grade evidence alignment, not prose polish.

## Module 4 — Ethical AI is workflow design

Move beyond abstract principle lists. Ask who is affected, what the system actually does, what data it needs, how errors propagate, and who can intervene.

Use the [Ethical AI Scenario Auditor](../../projects/ethical-ai-scenario-auditor/) to examine:

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

Assign groups the same scenario but different perspectives:
- person affected by the system;
- program owner;
- data steward;
- security/privacy lead;
- executive sponsor.

Each group identifies its three highest-priority risks and one design change. Compare what became visible only when the perspective changed.

## Module 5 — Red-team the workflow, not just the answer

Ask learners to test plausible failure paths:

- What if the input is wrong, incomplete, adversarial, or out of date?
- What if a user trusts the output too much?
- What if the system behaves differently across populations or contexts?
- What if a vendor changes a model or feature?
- What if the record of how a decision was produced is lost?
- What if a person needs to challenge the result?
- What if the safest answer is to use a non-AI process?

The goal is not to “break the model” for sport. It is to discover where the surrounding process needs controls.

## Module 6 — Applied capstone

### Scenario

A team proposes an AI assistant that summarizes intake notes and recommends follow-up resources.

### Deliverables

1. A purpose statement and explicit non-goals.
2. A data-minimization plan.
3. An evidence-safe prompt.
4. A risk and mitigation table with owners.
5. A human-review and contestability pathway.
6. A provenance/logging plan.
7. A small pilot and evaluation design.
8. A go / revise / do-not-deploy-yet recommendation with conditions.

### Evaluation rubric

| Dimension | Strong evidence |
| --- | --- |
| Task design | Purpose, audience, constraints, and non-goals are explicit. |
| Evidence use | Claims are traceable; unsupported claims are narrowed or flagged. |
| Risk reasoning | Risks are scenario-specific rather than copied from a generic list. |
| Mitigation quality | Controls change the workflow and have owners/evidence, not just policy language. |
| Human oversight | Review is meaningful, timely, and empowered to change outcomes. |
| Contestability | Affected people can correct information or reach a human. |
| Provenance | Material sources, instructions, versions, and decisions can be traced. |
| Evaluation | Success and harm indicators are measurable and revisited after launch. |

## Instructor notes

- Avoid grading students on prompt length.
- Reward explicit uncertainty and appropriate refusal to overclaim.
- Use low-stakes examples before high-impact health, education, employment, or public-benefit scenarios.
- When a task involves sensitive or identifying information, teach minimization before teaching optimization.
- Require learners to state what the tool cannot establish.
- Treat ethical review as iterative: discovery, design, pilot, launch, and monitoring can surface different risks.

## Portfolio / professional use

The kit demonstrates curriculum architecture, responsible-AI judgment, prompt engineering, evidence synthesis, assessment design, and interactive learning design. It can be adapted for higher education, faculty development, workforce training, professional learning, or internal AI governance education without presenting a checklist as a legal-compliance determination.
