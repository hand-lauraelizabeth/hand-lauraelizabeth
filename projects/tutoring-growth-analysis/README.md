# Tutoring growth analysis in R

A reproducible program-evaluation example that models pre/post growth while accounting for repeated observations and class structure.

## Analytical question

When groups begin at different levels, post-test averages alone are not enough to evaluate relative growth. This analysis estimates whether change from fall to spring differs by tutoring status.

## Methods demonstrated

- Synthetic-data generation with a fixed random seed
- Tidy reshaping with `pivot_longer()`
- Mixed-effects modeling with `lme4::lmer()`
- Random intercepts for class and student
- Interaction-based estimation of differential growth
- Confidence intervals with `broom.mixed`
- Plain-language summary statistics alongside the model

## Reproduce

Run `analysis.R` with:

```r
install.packages(c("tidyverse", "lme4", "broom.mixed"))
```

The script generates a synthetic dataset, fits the model, and prints both the interaction estimate and simple mean-growth summaries.

## Why mixed effects?

Each learner contributes repeated observations, and learners are nested within classes. Random intercepts represent those dependencies more appropriately than treating every score as independent.

## Interpretation

The synthetic dataset makes the complete analytical workflow reproducible. The project demonstrates model specification, uncertainty-aware reporting, and the distinction between an estimated association and a causal claim.

## Next extensions

- Quarto report
- Data dictionary
- Diagnostic plots and model checks
- Sensitivity analysis
- One-page stakeholder summary
