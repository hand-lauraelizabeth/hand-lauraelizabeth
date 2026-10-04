#!/usr/bin/env python3
"""Coverage/fairness diagnostic for recommendation evidence.

This tool audits whether evidence availability, review triggers, and recommendation
stability differ across declared institutional contexts. It does not use protected
attributes to alter recommendations and does not declare a disparity 'fair' or
'unfair' from a threshold alone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def audit(context: pd.DataFrame, evidence: pd.DataFrame, review: pd.DataFrame,
          stability: pd.DataFrame | None, candidate_id: str, groups: list[str], min_n: int):
    if candidate_id not in context.columns:
        raise ValueError(f"context missing {candidate_id}")
    if context[candidate_id].duplicated().any():
        raise ValueError("context must contain one row per candidate")
    for g in groups:
        if g not in context.columns:
            raise ValueError(f"context missing grouping field: {g}")
    if candidate_id not in evidence.columns or "evidence_state" not in evidence.columns:
        raise ValueError("evidence file must contain candidate ID and evidence_state")

    ev = evidence.copy()
    ev["observed"] = ev["evidence_state"].eq("observed").astype(int)
    ev_candidate = ev.groupby(candidate_id).agg(
        evidence_records=("evidence_state", "size"),
        observed_records=("observed", "sum")
    ).reset_index()
    ev_candidate["evidence_coverage_rate"] = ev_candidate["observed_records"] / ev_candidate["evidence_records"]

    if candidate_id in review.columns and not review.empty:
        rv = review.groupby(candidate_id).size().reset_index(name="review_trigger_count")
    else:
        rv = pd.DataFrame(columns=[candidate_id, "review_trigger_count"])

    base = context.merge(ev_candidate, on=candidate_id, how="left").merge(rv, on=candidate_id, how="left")
    base["review_trigger_count"] = num(base["review_trigger_count"]).fillna(0)
    base["has_review_trigger"] = base["review_trigger_count"].gt(0)

    if stability is not None:
        keep = [c for c in [candidate_id, "rank_range", "top_k_persistence", "rank_std"] if c in stability.columns]
        base = base.merge(stability[keep], on=candidate_id, how="left")
        for c in keep:
            if c != candidate_id:
                base[c] = num(base[c])

    rows = []
    for group_field in groups:
        for group_value, g in base.groupby(group_field, dropna=False):
            n = g[candidate_id].nunique()
            row = {
                "group_field": group_field,
                "group_value": group_value,
                "candidate_count": n,
                "small_group_flag": n < min_n,
                "mean_evidence_coverage_rate": g["evidence_coverage_rate"].mean(),
                "candidates_with_review_trigger": int(g["has_review_trigger"].sum()),
                "review_trigger_rate": g["has_review_trigger"].mean(),
                "mean_review_trigger_count": g["review_trigger_count"].mean(),
            }
            if "rank_range" in g.columns:
                row["mean_rank_range"] = g["rank_range"].mean()
            if "top_k_persistence" in g.columns:
                row["mean_top_k_persistence"] = g["top_k_persistence"].mean()
            if "rank_std" in g.columns:
                row["mean_rank_std"] = g["rank_std"].mean()
            rows.append(row)
    groups_out = pd.DataFrame(rows)

    # Compare each group only to the overall population for diagnostic deltas.
    overall_cov = base["evidence_coverage_rate"].mean()
    overall_review = base["has_review_trigger"].mean()
    groups_out["coverage_delta_vs_overall"] = groups_out["mean_evidence_coverage_rate"] - overall_cov
    groups_out["review_rate_delta_vs_overall"] = groups_out["review_trigger_rate"] - overall_review

    # Review queue: small samples and largest absolute diagnostic deltas. No universal fairness threshold is invented.
    groups_out["abs_coverage_delta"] = groups_out["coverage_delta_vs_overall"].abs()
    groups_out["abs_review_delta"] = groups_out["review_rate_delta_vs_overall"].abs()
    queue = groups_out.sort_values(
        ["small_group_flag", "abs_coverage_delta", "abs_review_delta"],
        ascending=[False, False, False]
    ).copy()
    queue["review_reason"] = queue.apply(
        lambda r: "small_group_interpret_cautiously" if r["small_group_flag"] else "largest_observed_coverage_or_review_delta",
        axis=1
    )

    summary = {
        "candidate_count": int(base[candidate_id].nunique()),
        "grouping_fields": groups,
        "group_rows": int(len(groups_out)),
        "minimum_group_size_for_non_small_flag": min_n,
        "overall_evidence_coverage_rate": None if pd.isna(overall_cov) else float(overall_cov),
        "overall_review_trigger_rate": None if pd.isna(overall_review) else float(overall_review),
        "interpretation": "Differences are diagnostic signals requiring contextual review; they are not proof of bias or fairness. Small groups must not be overinterpreted."
    }
    return base, groups_out.drop(columns=["abs_coverage_delta", "abs_review_delta"]), queue, summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--context", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--review-queue", type=Path, required=True)
    p.add_argument("--stability", type=Path)
    p.add_argument("--candidate-id", default="candidate_id")
    p.add_argument("--group", action="append", required=True, dest="groups")
    p.add_argument("--min-n", type=int, default=20)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.min_n < 1:
        raise ValueError("min-n must be >= 1")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stability = read(args.stability) if args.stability else None
    base, groups, queue, summary = audit(read(args.context), read(args.evidence), read(args.review_queue), stability,
                                         args.candidate_id, args.groups, args.min_n)
    base.to_csv(args.out_dir / "recommendation_candidate_diagnostic.csv", index=False)
    groups.to_csv(args.out_dir / "recommendation_group_coverage_diagnostic.csv", index=False)
    queue.to_csv(args.out_dir / "recommendation_group_review_queue.csv", index=False)
    (args.out_dir / "recommendation_coverage_fairness_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
