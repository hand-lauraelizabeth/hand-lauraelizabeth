# Tutoring growth analysis — portfolio demonstration
# Synthetic data only. This script does not represent a documented program result.

library(tidyverse)
library(lme4)
library(broom.mixed)

set.seed(20261004)

n_classes <- 8
students_per_class <- 20

students <- tibble(
  student_id = sprintf("S%03d", 1:(n_classes * students_per_class)),
  class_id = rep(sprintf("C%02d", 1:n_classes), each = students_per_class),
  tutored = rep(c(TRUE, TRUE, TRUE, TRUE, FALSE, FALSE, FALSE, FALSE),
                each = students_per_class)
) |>
  mutate(
    class_effect = rep(rnorm(n_classes, 0, 3), each = students_per_class),
    baseline = rnorm(n(), mean = 68, sd = 8) + class_effect,
    individual_growth = rnorm(n(), mean = 4, sd = 2),
    tutoring_increment = if_else(tutored, rnorm(n(), mean = 5, sd = 1.5), 0),
    fall = round(pmin(pmax(baseline, 0), 100), 1),
    spring = round(
      pmin(pmax(baseline + individual_growth + tutoring_increment, 0), 100),
      1
    )
  ) |>
  select(student_id, class_id, tutored, fall, spring)

long <- students |>
  pivot_longer(
    cols = c(fall, spring),
    names_to = "term",
    values_to = "score"
  ) |>
  mutate(term = factor(term, levels = c("fall", "spring")))

model <- lmer(
  score ~ term * tutored + (1 | class_id) + (1 | student_id),
  data = long
)

interaction_result <- tidy(
  model,
  conf.int = TRUE,
  effects = "fixed"
) |>
  filter(str_detect(term, "term.*:tutored|tutored.*:term"))

print(interaction_result)

summary_table <- students |>
  summarise(
    n_students = n(),
    tutored_students = sum(tutored),
    comparison_students = sum(!tutored),
    mean_growth_tutored = mean(spring[tutored] - fall[tutored]),
    mean_growth_comparison = mean(spring[!tutored] - fall[!tutored])
  )

print(summary_table)

# Optional: write outputs for a rendered report or QA review.
# write_csv(students, "synthetic_scores.csv")
# write_csv(interaction_result, "model_interaction.csv")
