# Projects & Interactive Demonstrations

These projects combine working browser tools, inspectable source code, and research or analytical work samples. **Choose “Open interactive tool” to use a demonstration without downloading code.** Open the corresponding repository or source folder if you want to examine its implementation.

## Find a tool by what you need to do

Choose a task below rather than guessing which project name fits. These links open the **published website interface**; the source links in the table below are for inspecting implementation, not running it.

| I need to… | Start here | What to expect |
| --- | --- | --- |
| Compare colleges and explore possible programs | [College Search](https://www.lauraelizabethhand.com/resources/data-decision-making-tools/college-career-explorer/) | Explore institution-level evidence; verify current program offerings and admissions policies with the institution. |
| Check how my experience supports a job description | [Reverse ATS / Role Evidence Studio](https://www.lauraelizabethhand.com/resources/career-professional-development-tools/reverse-ats/) | Review evidence and gaps; a generated suggestion is not proof of experience or a hiring prediction. |
| Play a word-chain game and explore changes in meaning | [Meaning Drift](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/meaning-drift/) | Play the published WordNet-based game; valid links depend on word senses, and a review-branch curated prototype is not the live edition. |\n| Examine language in context | [Text Lens](https://www.lauraelizabethhand.com/resources/research-writing-tools/text-lens/) | Inspect text patterns and their surrounding passages before interpreting them. |
| Plan learning objectives and assessment | [Curriculum Planning Canvas](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/curriculum-planning-canvas/) | Draft a learning sequence and review alignment; instructional judgment stays with the educator. |
| Group learners using assessment evidence | [Standards Check](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/standards-check/) | Work with fictional results and adjustable mastery assumptions. |
| Examine a prompt or AI-assisted decision | [Prompt Literacy Debugger](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/prompt-literacy-debugger/) | Identify task, evidence, privacy and verification questions before using AI. |
| Map audience and CRM transitions | [Audience Lifecycle Planner](https://www.lauraelizabethhand.com/resources/project-operations-tools/audience-lifecycle-crm-migration-planner/) | Plan stages, data fields and migration controls; no live CRM connection. |

**Looking for a prototype?** A review-branch HTML file is not a published tool. Source-only candidates, including Objective–Evidence Mapper, Housing Records Organizer, Scenario Sensitivity Lab, and Rubric Calibration Lab, must pass their own acceptance and approval gates before they appear in the published-tool directory. Do not use a GitHub file viewer as evidence that a prototype has been deployed.

## Interactive browser tools

| Tool | Open interactive tool | Source and method |
| --- | --- | --- |
| College Search | [Explore U.S. institutions](https://www.lauraelizabethhand.com/resources/data-decision-making-tools/college-career-explorer/) | [National data, provenance and source contracts](college-career-matching/) |
| Reverse ATS / Role Evidence Studio | [Analyze role evidence](https://www.lauraelizabethhand.com/resources/career-professional-development-tools/reverse-ats/) | [Evidence modeling and claim-strength controls](reverse-ats-role-evidence-engine/) |
| Meaning Drift | [Play the word-chain game](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/meaning-drift/) | [Review-only curated prototype](https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/blob/review/semantic-chain-game-20261108/projects/meaning-bridges/index.html) |\n| Text Lens | [Analyze and compare texts](https://www.lauraelizabethhand.com/resources/research-writing-tools/text-lens/) | [Text-analysis methods](text-lens/) |
| Standards Check | [Group fictional assessment results](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/standards-check/) | [JavaScript implementation](standards-check/) |
| Prompt Literacy Debugger | [Diagnose a prompt](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/prompt-literacy-debugger/) | [Seven-dimension instructional model](prompt-literacy-debugger/) |
| Evidence-Safe Prompt Lab | [Build an evidence-conscious prompt](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/evidence-safe-prompt-lab/) | [Source-to-claim controls](evidence-safe-prompt-lab/) |
| Ethical AI Scenario Auditor | [Review an AI workflow](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/ethical-ai-scenario-auditor/) | [Risk and oversight methodology](ethical-ai-scenario-auditor/) |
| Audience Lifecycle & CRM Migration Planner | [Map an audience lifecycle](https://www.lauraelizabethhand.com/resources/project-operations-tools/audience-lifecycle-crm-migration-planner/) | [Workflow, migration and data-contract prototype](audience-lifecycle-crm-migration/) |

[Curriculum Planning Canvas](curriculum-planning-canvas/) offers the [interactive browser tool](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/curriculum-planning-canvas/), [inspectable source and browser tests](curriculum-planning-canvas/), and a [downloadable planning method](../resources/curriculum-lesson-design/Design_Around_a_Real_Decision_Curriculum_Planning_Canvas.md).

## Reproducible analysis and applied work

These are **projects and research demonstrations, not live browser applications**. They should not be mistaken for interactive tools.

- [Tutoring Growth Analysis in R](tutoring-growth-analysis/) — synthetic pre/post data and mixed-effects modeling.
- [Learning Analytics Portfolio](https://github.com/hand-lauraelizabeth/learning-analytics-portfolio) — synthetic engagement and conversion analysis.
- [Curriculum Portfolio Analytics](https://github.com/hand-lauraelizabeth/curriculum-portfolio-analytics) — portfolio reporting and curriculum metrics.
- [Stevenson Text Analysis](https://github.com/hand-lauraelizabeth/stevenson-text-analysis) — public-domain textual analysis and reproducible research.

See also the [portfolio case studies](https://www.lauraelizabethhand.com/portfolio/) and [complete tools and templates library](https://www.lauraelizabethhand.com/resources/).

## Use, accessibility, and data

Browser demonstrations use synthetic examples or user-supplied content. Avoid entering confidential institutional, client, learner, or candidate information. A GitHub `index.html` file is **source code**, not a hosted interface; use the linked website for an executable demonstration. Claims about source data, estimates, model results, and limitations are documented within each project. The WordPress interfaces are published, but complete browser, keyboard, screen-reader, and touch interaction regression testing is ongoing.
