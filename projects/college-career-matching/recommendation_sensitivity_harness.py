#!/usr/bin/env python3
"""Scenario-based recommendation sensitivity/stability harness.

This is a validation tool, not the production scoring model. It accepts already
normalized dimension values and an explicit scenario weight table, then measures
how candidate ordering changes across approved scenarios.

No default weights are invented here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def numeric(series: pd.Series, label: str) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce")
    if out.isna().any():
        bad = series[out.isna()].head(5).tolist()
        raise ValueError(f"{label} contains non-numeric/missing values; scoring sensitivity must not silently impute them: {bad}")
    return out.astype(float)


def run(candidates: pd.DataFrame, weights: pd.DataFrame, candidate_id: str, top_k: int):
    if candidate_id not in candidates.columns:
        raise ValueError(f"missing candidate ID: {candidate_id}")
    if candidates[candidate_id].duplicated().any():
        raise ValueError("candidate IDs must be unique")
    required = {"scenario_id", "dimension", "weight"}
    if not required.issubset(weights.columns):
        raise ValueError(f"weights must contain {sorted(required)}")
    if weights[["scenario_id", "dimension"]].duplicated().any():
        raise ValueError("duplicate scenario/dimension weight rows")

    weights = weights.copy()
    weights["weight_num"] = numeric(weights["weight"], "weight")
    if (weights["weight_num"] < 0).any():
        raise ValueError("negative weights are not supported by this validation contract")

    dimensions = sorted(weights["dimension"].unique())
    missing_dims = [d for d in dimensions if d not in candidates.columns]
    if missing_dims:
        raise ValueError(f"candidate table missing weighted dimensions: {missing_dims}")
    values = candidates[[candidate_id] + dimensions].copy()
    for d in dimensions:
        values[d] = numeric(values[d], d)

    scenario_rows = []
    for scenario_id, group in weights.groupby("scenario_id", sort=True):
        total_w = group["weight_num"].sum()
        if total_w <= 0:
            raise ValueError(f"scenario {scenario_id} has no positive weight")
        w = {r.dimension: r.weight_num / total_w for r in group.itertuples()}
        score = pd.Series(0.0, index=values.index)
        for d in dimensions:
            score += values[d] * w.get(d, 0.0)
        tmp = pd.DataFrame({candidate_id: values[candidate_id], "scenario_id": scenario_id, "scenario_score": score})
        tmp = tmp.sort_values(["scenario_score", candidate_id], ascending=[False, True], kind="mergesort").reset_index(drop=True)
        tmp["rank"] = tmp.index + 1
        tmp["top_k_flag"] = tmp["rank"] <= top_k
        scenario_rows.append(tmp)
    scenarios = pd.concat(scenario_rows, ignore_index=True)

    stability = scenarios.groupby(candidate_id).agg(
        scenario_count=("scenario_id", "nunique"),
        best_rank=("rank", "min"),
        worst_rank=("rank", "max"),
        mean_rank=("rank", "mean"),
        rank_std=("rank", "std"),
        top_k_count=("top_k_flag", "sum"),
        min_score=("scenario_score", "min"),
        max_score=("scenario_score", "max"),
    ).reset_index()
    stability["rank_range"] = stability["worst_rank"] - stability["best_rank"]
    stability["top_k_persistence"] = stability["top_k_count"] / stability["scenario_count"]
    stability["rank_std"] = stability["rank_std"].fillna(0.0)

    # Dimension leave-one-out scenarios are generated only from an explicitly named baseline.
    loo_rows = []
    if "baseline" in set(weights["scenario_id"]):
        base = weights[weights["scenario_id"].eq("baseline")][["dimension", "weight_num"]]
        for dropped in base.loc[base["weight_num"] > 0, "dimension"]:
            g = base[~base["dimension"].eq(dropped)].copy()
            total = g["weight_num"].sum()
            if total <= 0:
                continue
            g["scenario_id"] = f"leave_out::{dropped}"
            g["weight"] = g["weight_num"] / total
            loo_rows.append(g[["scenario_id", "dimension", "weight"]])
    loo = pd.concat(loo_rows, ignore_index=True) if loo_rows else pd.DataFrame(columns=["scenario_id", "dimension", "weight"])

    summary = {
        "candidate_count": int(candidates[candidate_id].nunique()),
        "scenario_count": int(weights["scenario_id"].nunique()),
        "dimension_count": len(dimensions),
        "top_k": top_k,
        "stable_top_k_candidates": int((stability["top_k_persistence"] == 1).sum()),
        "never_top_k_candidates": int((stability["top_k_persistence"] == 0).sum()),
        "generated_leave_one_out_scenarios": int(loo["scenario_id"].nunique()) if not loo.empty else 0,
        "interpretation": "Rank movement is a validation signal, not a penalty. Thresholds for acceptable instability must be set after empirical review."
    }
    return scenarios, stability, loo, summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--weights", type=Path, required=True)
    p.add_argument("--candidate-id", default="candidate_id")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.top_k < 1:
        raise ValueError("top-k must be >= 1")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    scenarios, stability, loo, summary = run(read(args.candidates), read(args.weights), args.candidate_id, args.top_k)
    scenarios.to_csv(args.out_dir / "recommendation_sensitivity.csv", index=False)
    stability.to_csv(args.out_dir / "recommendation_stability.csv", index=False)
    loo.to_csv(args.out_dir / "recommendation_leave_one_out_scenarios.csv", index=False)
    (args.out_dir / "recommendation_sensitivity_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
