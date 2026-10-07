# Reverse ATS Is the Wrong Question: Build an Evidence Map Instead

Most job-matching tools start with a deceptively simple question: *How many words in this job description also appear in my resume?*

That can be useful, but it is not the same as asking whether someone is qualified for a role. A keyword can be visible without proving depth. Relevant experience can be real without being visible. A job posting can ask for leadership when a resume only shows coordination, or require eight years of experience when overlapping roles make a simple date count misleading.

I built the **Role Evidence Engine** to make those distinctions explicit.

## From keyword matching to evidence matching

The tool treats a job posting as a set of different requirement types rather than one bag of terms. Hard requirements, preferred qualifications, responsibilities, tools, context, and seniority signals are separated so they can be evaluated differently.

Candidate material is also decomposed into evidence nodes. Each node retains its source and can carry reviewed metadata such as dates, role or project, source reference, disclosure limits, authority or scope notes, and verification state.

That changes the question from “Did this word appear?” to “What evidence supports this requirement, where did it come from, how strong is it, and is it safe to use?”

## Visibility is not support

One of the most important design decisions is a separate **Visibility** and **Reviewed Support** layer.

A resume may contain the word “budget,” for example. That does not establish budget authority. A portfolio may mention Python without establishing current independent proficiency. A team outcome may be measurable without proving that one person caused it.

The engine therefore keeps visible evidence distinct from evidence that is self-attested, source-corroborated, verified, or blocked from external use.

This is deliberately conservative. The goal is not to manufacture a stronger application. It is to identify the strongest application that the evidence can actually support.

## Not every gap is a capability gap

The engine classifies gaps so the next action fits the actual problem:

- **Material capability gap:** the experience appears genuinely absent.
- **Evidence visibility gap:** the experience may exist, but it is not legible in the supplied materials.
- **Chronology gap:** dates or progression are not clear enough to support an experience threshold.
- **Depth or recency gap:** a tool or method appears, but current independent use is unclear.
- **Authority gap:** participation is visible, but ownership or decision rights are not.
- **Context gap:** the transferable skill is present, but the exact setting differs.
- **Portfolio-proof gap:** the claim exists without a strong public demonstration.
- **Verification gap:** stronger wording may be possible, but the source needs to be recovered first.

That distinction matters because the remedies are different. A real capability gap may justify training. A visibility gap may require one better resume bullet. An authority gap may require recovering a contract, org chart, project record, or other source before changing the wording at all.

## Concurrent work should not inflate experience

Career histories are rarely perfectly linear. People consult, teach, freelance, study, or hold overlapping roles.

The current prototype allows reviewed date intervals to be entered for evidence nodes and de-duplicates overlapping calendar years when checking experience thresholds. Concurrent roles can add breadth, but they should not silently turn five calendar years into ten years of experience.

## A ceiling on application language

The claim guardrail is designed around a simple rule: **generated wording cannot be stronger than the reviewed evidence behind it.**

Unreviewed evidence stays in the review queue. Self-attested evidence is labeled as such. Source-corroborated or verified evidence can support stronger wording, while confidentiality settings can require anonymization or block external use entirely.

The result is less like an “ATS score” and more like an evidence audit.

## Why I built it

My work has repeatedly sat between systems, people, and evidence: career services, curriculum and learning strategy, program operations, analytics, CRM/CMS workflows, and technical teaching. I wanted a tool that reflected the way strong career advising actually works.

A useful career tool should be able to say:

> You may be able to do this, but your current materials do not prove it yet.

It should also be able to say:

> This is visible, but the wording you want to use would overstate the evidence.

Those are more useful conclusions than a percentage match.

## What the prototype demonstrates

The browser prototype currently includes:

- job-description parsing by requirement type;
- source-aware candidate evidence nodes;
- requirement-to-evidence provenance;
- visibility versus reviewed-support states;
- chronology checks that account for concurrent roles;
- explicit checks for years, degree, and required-tool conditions;
- gap classification and next-action guidance;
- confidentiality-aware evidence export;
- claim-strength guardrails; and
- CSV/JSON exports for further review.

The project is local-first by design. It does not claim to reproduce Workday, Greenhouse, iCIMS, Ashby, Taleo, or any employer's proprietary ranking system.

## What comes next

The next development stage is cross-posting analysis: looking across a set of target roles to identify repeated hiring signals, evidence bottlenecks, compensation-tier differentiators, and the portfolio work most likely to improve future applications.

The larger goal is not to “beat the ATS.” It is to make career evidence more legible, more honest, and more useful for decision-making.

---

**Project status:** active prototype. Public demonstration data should remain synthetic or explicitly cleared for publication. The tool's outputs are decision support, not hiring predictions.
