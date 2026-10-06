# O*NET Career Preference Governance

**Status:** reviewed O*NET 31.0 work-activity mappings approved for service-gated career-first use; descriptive alignment only.

## Purpose

This contract governs the plain-language work-characteristic preferences used by the College + Career Matching Tool. It prevents a convenient UI phrase from being mapped to an unrelated O*NET construct merely because the construct sounds similar.

The public matcher may expose a career-preference question only when:

1. the question has an approved registry entry;
2. the active service has loaded the matching governed O*NET evidence;
3. the submitted attribute ID, operator, and scale exactly match that registry; and
4. missing/suppressed evidence remains missing rather than becoming mismatch.

## Source and scale

Production source: **O*NET Database 31.0**, Work Activities, August 2026 release.

Approved scale: **Importance (`IM`)**, range **1–5**.

The question wording deliberately asks whether an activity should be an important part of the user's work. It therefore maps to O*NET Work Activity Importance rather than to an ability, work style, or the separate Work Activity Level scale.

## Approved mappings

| Question | O*NET element | Governed attribute ID | Operator |
| --- | --- | --- | --- |
| Analyzing data or information is important | 4.A.2.a.4 — Analyzing Data or Information | `onet31:work_activity:4.A.2.a.4:IM` | `higher_preferred` |
| Making decisions and solving problems is important | 4.A.2.b.1 — Making Decisions and Solving Problems | `onet31:work_activity:4.A.2.b.1:IM` | `higher_preferred` |
| Thinking creatively is important | 4.A.2.b.2 — Thinking Creatively | `onet31:work_activity:4.A.2.b.2:IM` | `higher_preferred` |

The prior draft question combining analysis and problem solving was rejected because it collapsed two distinct O*NET work activities into one preference.

## Why these are not abilities or work styles

The creativity question maps to **Thinking Creatively**, not the **Originality** ability and not the **Innovation** work style. The user's preference is about creative activity being part of the job, not about possessing a worker ability or personality/work-style tendency.

Likewise, the analysis and problem-solving questions use the relevant Work Activities rather than Critical Thinking or Complex Problem Solving skill constructs. The UI is asking what the work should involve, not asking the user to self-assess skill proficiency.

## SOC identity policy

The existing college-career pathway layer is keyed to six-digit SOCs. O*NET may publish multiple detailed specialty occupations beneath one six-digit SOC. For this reviewed preference layer:

- only O*NET-SOC rows ending in `.00` are eligible;
- the terminal `.00` is stripped to the base six-digit SOC;
- `.01`, `.02`, and other specialty profiles are not averaged into a parent SOC;
- absence of a `.00` reviewed attribute remains a coverage gap.

This avoids manufacturing a composite occupational profile without an authoritative aggregation rule.

## Missingness and suppression

Observed O*NET values may contribute to pathway alignment. Suppressed, not-relevant, missing, or absent attributes do not receive a numeric alignment value.

Missing evidence lowers coverage. It does not become zero alignment and does not imply that the occupation lacks the activity.

## Alignment semantics

For an explicit `higher_preferred` preference on the 1–5 Importance scale:

`alignment = (observed_importance - 1) / 4`, clipped to `[0,1]`.

Multiple selected work-characteristic preferences are combined at the occupation-pathway level using only observed evidence and the user's explicit importance values. Coverage remains separate from alignment.

Program-level display may summarize pathway alignment using median/min/max and pathway coverage. The service does not choose a single occupation merely because it aligns best.

## Product boundary

The current public/staging implementation is **descriptive**:

- career-preference alignment does not change service ordering;
- the index is not a probability of satisfaction, persistence, employment, or placement;
- it is not a graduate-outcome measure;
- no hidden work-characteristic preference is created when the visitor skips the questions;
- the browser cannot invent or rename O*NET attribute IDs;
- controls remain hidden unless the active service advertises reviewed, loaded attributes through `/options`.

Ranking calibration remains separately gated.
