# Standards Check: browser-based reteach grouping tool

A lightweight JavaScript tool for turning standards-level assessment results into actionable reteach groups.

## What it does

- Applies an adjustable mastery threshold
- Identifies learners below the threshold for each standard
- Groups learners by the concept that needs reteaching rather than by total score
- Runs locally in a browser with no installation

## Why this design

Aggregate scores can hide which specific concepts need attention. The tool keeps the interface aligned to the instructional decision: **what needs reteaching, and who needs it?**

## Technical implementation

- Vanilla JavaScript
- DOM manipulation
- Responsive browser interface
- Adjustable range input
- Dynamic table rendering
- Standards-level filtering and grouping
- Local sample-data generation

## Run it

Open `index.html` in any modern browser.

The demonstration uses sample data so the full workflow can be inspected without exposing learner information.

## Current boundaries

This browser demonstration uses generated sample results and an adjustable mastery threshold. It does not import actual learner records, store classroom configurations, or export reteaching groups. Treat the suggested groupings as a planning aid to review against learners' actual work, not a diagnosis of learning needs.
