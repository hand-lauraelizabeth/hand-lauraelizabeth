# Standards Check — Assessment to Instruction Planner

**[Use the interactive WordPress interface](https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/standards-check/)** · [Inspect source](index.html)

An install-free, browser-local JavaScript planner for turning standards-level evidence into responsible next steps. Import your own CSV exported from Excel or Google Sheets, or explore a fictional two-date class.

## Import formats

- Wide: learner_id, assessment_date, Fractions, Argument writing (each standard as a separate column).
- Long: learner_id, standard, score, max_score, assessment_date.
- max_score and assessment_date are optional in long format. The default maximum is editable.
- learner_id aliases: student_id, student, learner, name and id.
- A blank score means missing evidence, not zero. Repeated dated learner-standard observations allow descriptive progress comparisons.

## Outputs

- Row-level import warnings for bad identifiers, duplicate learner-standard-date keys, invalid scores, incorrect column counts, and malformed dates.
- Coverage, mastery and below-threshold counts by standard using latest available records.
- Editable per-standard mastery rules and maximum small-group size.
- Prioritized reteaching rosters, separate missing-evidence queues, editable educator notes and targeted evidence-check prompts.
- Searchable latest-evidence matrix, dated score changes, two spreadsheet-compatible CSV exports and print view.

## Privacy and evidence limits

The application reads data in its browser tab without transmitting or persisting learner records. Use pseudonymous identifiers and institutional data-management standards. It is a planning aid, not a psychometric instrument: scores alone cannot diagnose misconceptions, accessibility needs or learner conditions. Score gains cannot be attributed to instruction without an appropriate evaluation design. Review actual learner work before acting.

## Run and test

Open index.html locally in a browser, or run the Node.js regression suite:

    node projects/standards-check/test.cjs

The tests run in GitHub Actions for relevant pull requests. Manual release gates remain: actual Chromium/Firefox/WebKit behavior, screen-reader navigation, browser zoom, and reopening exported CSV files in Excel and Google Sheets.
