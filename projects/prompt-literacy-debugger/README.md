# Prompt Literacy Debugger

A browser-based teaching tool for diagnosing a prompt before using it.

The tool treats prompting as **task specification**, not prompt magic. Learners examine seven dimensions:

1. task;
2. context and audience;
3. evidence boundary;
4. authority and guardrails;
5. output contract;
6. verification;
7. human responsibility.

It then generates a rebuild scaffold that preserves the original request while making missing requirements explicit.

## Why this is different from the Evidence-Safe Prompt Lab

The [Evidence-Safe Prompt Lab](../evidence-safe-prompt-lab/) helps users **compose** an evidence-conscious prompt.

The Prompt Literacy Debugger helps users **inspect and diagnose** a prompt they already have. It is meant to teach why a prompt succeeds or fails, not simply provide a stronger prompt on demand.

## Responsible-use design

The tool runs entirely in the browser. It does not call an AI API or transmit entered text.

It also adds decision gates when a user identifies:
- high-consequence use;
- internal/restricted information;
- sensitive, confidential, or identifying data.

Those gates are teaching prompts, not compliance determinations.

## Instructional use

A useful exercise is to give a class the same vague prompt and ask learners to rate the seven dimensions independently. Compare disagreements before revealing a revised scaffold.

This makes hidden assumptions visible and creates a natural discussion about:
- what the model was actually asked to do;
- what evidence it was allowed to rely on;
- what could be inferred;
- what needed verification;
- what remained a human decision.

## Framework alignment

The teaching design is consistent with current AI-literacy and responsible-AI frameworks that emphasize human agency, critical evaluation, risk management, and responsible use rather than treating AI proficiency as prompt technique alone:

- NIST, *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile* (NIST AI 600-1): https://doi.org/10.6028/NIST.AI.600-1
- UNESCO, *AI Competency Framework for Teachers* (2024): https://www.unesco.org/en/articles/ai-competency-framework-teachers
- UNESCO, *AI Competency Framework for Students* (2024): https://www.unesco.org/en/articles/ai-competency-framework-students
- OECD / European Commission, *Empowering Learners for the Age of AI: An AI Literacy Framework for Primary and Secondary Education* (2026): https://doi.org/10.1787/65cd27d4-en

These sources inform the educational framing; the tool is not an official implementation or certification instrument for any of them.
