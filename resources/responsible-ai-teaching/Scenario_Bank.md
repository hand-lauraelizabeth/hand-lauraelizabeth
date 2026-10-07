# Responsible AI Scenario Bank

Use these scenarios with the [Prompt Literacy Debugger](../../projects/prompt-literacy-debugger/), [Evidence-Safe Prompt Lab](../../projects/evidence-safe-prompt-lab/), and [Ethical AI Scenario Auditor](../../projects/ethical-ai-scenario-auditor/).

The scenarios deliberately vary in stakes, data sensitivity, reversibility, and the role AI plays in the workflow.

## 1. Low-stakes communications draft

A student organization wants to use AI to draft three versions of an event reminder for different audiences. The event details are public.

**Good for:** prompt specification, audience, output contract.

**Questions**
- What information is fixed and must not change?
- What tone differences are useful versus stereotyped?
- What facts should be verified before sending?
- Does a human need to review the final copy?

## 2. Research synthesis with incomplete evidence

A graduate student has five sources on AI in healthcare and asks an AI tool to determine whether the literature proves that AI improves patient outcomes.

**Good for:** evidence boundaries, overclaiming, citation integrity, uncertainty.

**Questions**
- What does “proves” imply?
- Are the sources comparable in population, intervention, and outcome?
- What should the system do when a claim is only partially supported?
- What evidence would be needed to make a stronger conclusion?

## 3. Workplace analytics narrative

A training team gives an AI assistant an aggregated spreadsheet of registrations, attendance, completion, and satisfaction and asks for an executive summary.

**Good for:** quantitative verification, interpretation limits, audience translation.

**Questions**
- Which calculations should be checked independently?
- What can the data show versus not show about causation?
- Which missing denominators or comparison groups matter?
- What decision is the executive summary meant to support?

## 4. Student-support notes

A university office proposes using AI to summarize student intake notes and recommend follow-up resources. Staff will review the recommendation before contacting the student.

**Good for:** data minimization, sensitive information, human oversight, contestability.

**Questions**
- What information is necessary for the task?
- What should never be inferred from the notes?
- How could a student correct inaccurate information?
- What would meaningful staff review look like?
- When should the workflow route directly to a human instead?

## 5. Candidate-screening support

A hiring team wants AI to rank applicants based on resumes and a role description. A recruiter will see the ranking before deciding whom to interview.

**Good for:** decision delegation, bias, explainability, documentation.

**Questions**
- Is ranking the right task, or would structured evidence extraction be safer?
- Which resume characteristics are legitimate job evidence?
- How might proxies reproduce bias?
- Can a candidate challenge or correct inaccurate information?
- What human decision rule prevents automation from becoming the actual gatekeeper?

## 6. Educational intervention recommendation

A school wants AI to identify students who may need additional academic support using grades, attendance, assignment data, and teacher comments.

**Good for:** high-consequence use, sensitive data, differential impact, monitoring.

**Questions**
- What is the intended benefit, and what would count as harm?
- Which data are necessary?
- Could the model confuse structural barriers with student ability or motivation?
- What happens after a student is flagged?
- What false-positive and false-negative outcomes matter?
- Who can review or overturn the recommendation?

## 7. Health-information summary

A patient-facing service considers using AI to summarize uploaded medical records and suggest questions a user may want to ask a clinician. It will not diagnose or recommend treatment.

**Good for:** high stakes, uncertainty, boundary design, provenance.

**Questions**
- How should the tool distinguish summarization from diagnosis?
- What records or sections should be preserved verbatim?
- What uncertainty or missingness must be surfaced?
- How should users verify the summary?
- What happens if the model misses a clinically important detail?

## 8. Public-policy briefing

A policy team asks AI to synthesize public comments and research into a briefing for decision makers.

**Good for:** representativeness, provenance, summarization bias, evidence weighting.

**Questions**
- Are public comments evidence of prevalence, experience, preference, or something else?
- How should minority or dissenting views be represented?
- Which claims require independent source verification?
- Can the synthesis be reproduced from the retained evidence?
- What decisions should remain outside the model's remit?

## Teaching variations

### Change one variable

Give two groups the same scenario but change one condition:
- public data vs confidential data;
- brainstorming vs decision support;
- optional recommendation vs automatic action;
- low consequence vs high consequence;
- individual use vs organization-wide deployment.

Ask what changes in the prompt, workflow, review process, and decision to use AI at all.

### Perspective rotation

Assign learners different roles:
- affected person;
- instructor/practitioner;
- program owner;
- data steward;
- security/privacy lead;
- executive sponsor.

Each role identifies:
1. the most important benefit;
2. the most important risk;
3. the evidence needed before deployment;
4. one control that changes the workflow rather than merely adding policy language.

### Prompt repair

For any scenario, start with a deliberately weak prompt:

> Review this information and tell me what we should do.

Learners should diagnose what is missing before writing a better version.
