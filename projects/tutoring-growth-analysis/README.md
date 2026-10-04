# Tutoring growth analysis in R

A reproducible demonstration of how I would move from a program-evaluation question to an analysis that accounts for baseline differences and clustered/repeated observations.

## Question

If tutored and comparison classes begin at different levels, raw post-test averages are not enough to evaluate relative growth. This example models change from fall to spring and estimates whether the change differs by tutoring status.

## Methods demonstrated

- Synthetic-data generation with a fixed random seed
- Tidy data reshaping with `pivot_longer()`
- Mixed-effects modeling with `lme4::lmer()`
- Random intercepts for class and student
- Interaction-based estimation of differential growth
- Confidence intervals with `broom.mixed`
- Plain-language summary statistics alongside the model

## Reproduce

Run `analysis.R` with these packages installed:

```r
install.packages(c("tidyverse", "lme4", "broom.mixed"))
```

The script generates its own synthetic dataset, fits the model, and prints both the interaction estimate and simple mean-growth summaries.

## Evidence boundary

All observations in this repository are **synthetic**. The project demonstrates analytical method and reproducibility; it does not establish that a particular tutoring program produced the simulated effect.

That distinction is intentional. A production evaluation would additionally document assignment or selection mechanisms, missing-data rules, measurement validity, model diagnostics, sensitivity analyses, and contextual limitations before making causal or program-impact claims.

## Why mixed effects?

Each learner contributes repeated observations, and learners are nested within classes. Random intercepts represent those dependencies more appropriately than treating every score as an independent observation.

## Next extension

A fuller version can be rendered in Quarto with a data dictionary, diagnostic plots, model checks, an executive summary, and an explicitly non-causal interpretation where random assignment is absent.
