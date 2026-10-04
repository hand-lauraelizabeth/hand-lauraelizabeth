#!/usr/bin/env python3
"""Pre-score evidence audit for College + Career Matching Tool.

This script intentionally does not calculate a recommendation score. It audits
whether candidate rows contain the evidence required to make scoring defensible.

Inputs
------
--candidates CSV: model-ready candidate rows. Must contain a stable candidate ID.
--policy CSV: one row per audited field with columns:
    field, dimension, required, missing_policy, evidence_strength, review_if_missing
Optional policy columns are preserved in field-level output.

Outputs
-------
recommendation_input_missingness.csv
recommendation_evidence_coverage.csv
recommendation_review_queue.csv
recommendation_validation_summary.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd

MISSING_TOKENS = {"", "NA", "N/A", "NULL", "NONE"}
EXPLICIT_EVIDENCE_STATES = {
    "unknown", "not_applicable", "suppressed", "not_pre_evaluated",
    "unresolved_identity", "not_published_for_geography", "source_not_covered"
}


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def classify(value: str, policy: str) -> str:
    v = str(value).strip()
    low = v.lower()
    if low in EXPLICIT_EVIDENCE_STATES:
        return low
    if v.upper() in MISSING_TOKENS:
        return policy.strip().lower() if policy.strip() else "unknown"
    return "observed"


def audit(candidates: pd.DataFrame, policy: pd.DataFrame, candidate_id: str):
    if candidate_id not in candidates.columns:
        raise ValueError(f"candidate table missing ID column: {candidate_id}")
    required_policy = ["field", "dimension", "required", "missing_policy", "evidence_strength", "review_if_missing"]
    missing_policy_cols = [c for c in required_policy if c not in policy.columns]
    if missing_policy_cols:
        raise ValueError(f"policy missing columns: {missing_policy_cols}")
    if candidates[candidate_id].duplicated().any():
        raise ValueError("candidate IDs must be unique before scoring")
    if policy["field"].duplicated().any():
        raise ValueError("field-policy manifest contains duplicate fields")

    records = []
    reviews = []
    for _, p in policy.iterrows():
        field = p["field"].strip()
        if field not in candidates.columns:
            # Schema absence is different from row-level missingness.
            for cid in candidates[candidate_id]:
                rec = {candidate_id: cid, "field": field, "dimension": p["dimension"],
                       "evidence_state": "field_absent_from_candidate_schema",
                       "evidence_strength": p["evidence_strength"], "required": p["required"]}
                records.append(rec)
                if truthy(p["required"]) or truthy(p["review_if_missing"]):
                    reviews.append({candidate_id: cid, "dimension": p["dimension"], "field": field,
                                    "review_reason": "field_absent_from_candidate_schema"})
            continue

        for cid, value in zip(candidates[candidate_id], candidates[field]):
            state = classify(value, p["missing_policy"])
            rec = {candidate_id: cid, "field": field, "dimension": p["dimension"],
                   "evidence_state": state, "evidence_strength": p["evidence_strength"],
                   "required": p["required"]}
            records.append(rec)
            missing = state != "observed" and state != "not_applicable"
            if missing and (truthy(p["required"]) or truthy(p["review_if_missing"])):
                reviews.append({candidate_id: cid, "dimension": p["dimension"], "field": field,
                                "review_reason": state})

    detail = pd.DataFrame(records)
    review = pd.DataFrame(reviews, columns=[candidate_id, "dimension", "field", "review_reason"]).drop_duplicates()

    coverage = (detail.assign(observed=detail["evidence_state"].eq("observed").astype(int))
                .groupby(["dimension", "field", "evidence_state"], dropna=False)
                .size().reset_index(name="candidate_count"))

    total = int(candidates[candidate_id].nunique())
    review_candidates = int(review[candidate_id].nunique()) if not review.empty else 0
    summary = {
        "candidate_count": total,
        "audited_field_count": int(policy["field"].nunique()),
        "audit_record_count": int(len(detail)),
        "review_queue_record_count": int(len(review)),
        "candidates_with_review_trigger": review_candidates,
        "candidates_without_review_trigger": total - review_candidates,
        "scoring_gate": "BLOCKED_PENDING_REVIEW" if review_candidates else "ELIGIBLE_FOR_NEXT_VALIDATION_STAGE",
        "note": "Eligibility here does not authorize production scoring; sensitivity, fairness/coverage, explanation, accessibility, and manual-review gates remain."
    }
    return detail, coverage, review, summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--candidate-id", default="candidate_id")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    detail, coverage, review, summary = audit(read(args.candidates), read(args.policy), args.candidate_id)
    detail.to_csv(args.out_dir / "recommendation_input_missingness.csv", index=False)
    coverage.to_csv(args.out_dir / "recommendation_evidence_coverage.csv", index=False)
    review.to_csv(args.out_dir / "recommendation_review_queue.csv", index=False)
    (args.out_dir / "recommendation_validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
