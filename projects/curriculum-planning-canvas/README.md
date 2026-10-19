# Curriculum Planning Canvas — Interactive

**[Use the live interactive planning canvas](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/curriculum-planning-canvas/)**

A browser-based curriculum design workspace for moving from learner context and authentic performance to measurable objectives, aligned activities, assessment evidence, accessible delivery, and revision plans. The fields contain **expandable worked examples**; the **Load synthetic example** control supplies a complete planning scenario.

## Using the canvas

1. Describe a concrete learner decision, product, or action and how success will be demonstrated.
2. Write measurable learning objectives using an observable verb, scope/conditions, a corresponding assessment, and practice.
3. Build a sequence that prepares learners for the final performance. Keep feedback, transfer, accessibility, and facilitator handoff visible.
4. Review alignment, export a structured JSON plan, copy a readable brief, or print. Browser-local saving is optional.

Every section is a direct, accessible fragment link, and basic navigation continues to work without JavaScript. The saved plan and exported file can include information the user entered; avoid sensitive learner data.

## Method and limitations

The method draws on backward design and constructive alignment, observable objectives, and [CAST Universal Design for Learning Guidelines 3.0](https://udlguidelines.cast.org/), particularly examples, multiple means of participation and expression, and graduated support. The canvas is a planning aid rather than an automated accreditation, accessibility certification, or measure of teaching quality.

## Source and QA

- [Run locally](index.html) by opening the standalone HTML file.
- [Browser regression tests](tests/browser_scenarios.py) cover direct tab clicks, keyboard navigation, field examples, state persistence, synthetic planning, and review.
- The test suite includes a CSS-only navigation fallback and an optional live WordPress URL. Browser testing is not a substitute for manual mobile zoom or assistive-technology review.

[Browse the full project gallery](../README.md) · [Download curriculum resources](../../resources/curriculum-lesson-design/).
