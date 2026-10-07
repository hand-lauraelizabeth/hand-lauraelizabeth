# Role Evidence Engine — v2.1

An explainable, local-first prototype for comparing a job description with documented candidate evidence.

## What v2.1 adds

- pasted job-description parsing;
- visible classification of hard requirements, preferred signals, responsibilities, scope/seniority signals, tools, and context;
- candidate-evidence comparison;
- hard-requirement visibility;
- gap labels that distinguish possible material gaps from visibility, chronology, authority/scope, and depth/recency gaps;
- next-action guidance;
- CSV export of the requirement matrix.

## What it does **not** claim

This is not an emulator for Workday, Greenhouse, iCIMS, Taleo, Ashby, or any employer’s proprietary ranking process. The heuristic output is a diagnostic aid. Keyword presence does not prove proficiency, recency, authority, causality, or job performance.

## Roadmap

v2.2a: source-aware provenance scaffold implemented ([resume] / [portfolio] / [public] / [document] / [user])
v2.2b: statement-level evidence graph implemented with source, dates/metrics, scope/depth signals, competencies, and JSON export
v2.2c: human-reviewed evidence metadata and claim-strength guardrails implemented
v2.3: ATS visibility is now separated from reviewed support; requirement rows distinguish visible-but-unreviewed evidence from source-corroborated/verified support, confidentiality-aware export is enforced, and reviewed metadata survives reanalysis  
v2.4: executive-scope / compensation-tier model  
v2.5: claim guardrails + resume/interview/portfolio actions  
v2.6: multi-posting career-level pattern analysis

The full product/scoring specification is maintained separately in the user's working Drive.
