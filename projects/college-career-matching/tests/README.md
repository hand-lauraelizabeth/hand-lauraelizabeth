# Synthetic Recommendation Architecture Tests

These tests use deliberately fictional identifiers and values. They are designed to verify recommendation-system semantics and guardrails without reproducing confidential student, institution, employer, or licensed labor-market records.

Current regression coverage checks that:

- an observed hard-constraint mismatch excludes a candidate;
- unknown evidence remains eligible-with-unknown unless an explicit policy requires verified evidence;
- missing evidence is not converted to zero;
- partial within-dimension aggregation is blocked unless renormalization is explicitly allowed;
- only explicitly stated user priorities receive dimension weights;
- many-to-many program-to-occupation pathways remain visible rather than collapsing to one occupation;
- a failed required release check blocks release;
- a failed prerequisite blocks downstream pipeline execution.

Run from the repository root with:

```bash
python -m unittest projects/college-career-matching/tests/test_synthetic_recommendation_architecture.py
```

## Scope limitation

This first suite tests architectural invariants with small pure-Python fixtures. It does not validate empirical weights, normalization reference populations, source coverage, predictive validity, fairness outcomes, or recommendation quality. Those require authoritative/versioned source fixtures and approved validation criteria.

## Next regression block

Add integration fixtures that invoke the actual project scripts against tiny CSV/JSON inputs and compare produced artifacts to expected snapshots. Priority integration cases are candidate-universe constraints, feature registry, partial-dimension composition, career-pathway aggregation/alignment, pipeline dependency handling, and release-gate decisions.
