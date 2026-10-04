#!/usr/bin/env python3
"""Build auditable normalized recommendation dimensions without scoring candidates.

The engine consumes a candidate table and a versioned feature manifest. It does
not invent direction, reference bounds, feature weights, or missing-data rules.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd

REQUIRED_MANIFEST = [
    "feature", "dimension", "transform", "direction", "feature_weight",
    "missing_policy", "reference_id", "reference_min", "reference_max",
]
VALID_TRANSFORMS = {"identity_0_1", "minmax_reference"}
VALID_DIRECTIONS = {"higher_better", "lower_better"}
MISSING_TOKENS = {"", "NA", "N/A", "NULL", "NONE"}


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def num(value: str, label: str) -> float:
    try:
        return float(str(value).strip())
    except Exception as exc:
        raise ValueError(f"{label} must be numeric: {value!r}") from exc


def is_missing(value: str) -> bool:
    return str(value).strip().upper() in MISSING_TOKENS


def normalize_value(raw: str, row: pd.Series):
    if is_missing(raw):
        return None, (row["missing_policy"].strip().lower() or "unknown")
    x = num(raw, row["feature"])
    transform = row["transform"].strip()
    direction = row["direction"].strip()
    if transform not in VALID_TRANSFORMS:
        raise ValueError(f"unsupported transform {transform!r} for {row['feature']}")
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"unsupported direction {direction!r} for {row['feature']}")

    if transform == "identity_0_1":
        if not 0 <= x <= 1:
            raise ValueError(f"identity_0_1 value outside [0,1] for {row['feature']}: {x}")
        z = x
    else:
        lo = num(row["reference_min"], f"reference_min {row['feature']}")
        hi = num(row["reference_max"], f"reference_max {row['feature']}")
        if hi <= lo:
            raise ValueError(f"invalid reference range for {row['feature']}: {lo}, {hi}")
        # Clip to declared reference range; the manifest makes the clipping visible.
        z = (min(max(x, lo), hi) - lo) / (hi - lo)

    if direction == "lower_better":
        z = 1.0 - z
    return z, "observed"


def build(candidates: pd.DataFrame, manifest: pd.DataFrame, candidate_id: str):
    if candidate_id not in candidates.columns:
        raise ValueError(f"candidate table missing {candidate_id}")
    if candidates[candidate_id].duplicated().any():
        raise ValueError("candidate IDs are not unique at declared grain")
    missing_cols = [c for c in REQUIRED_MANIFEST if c not in manifest.columns]
    if missing_cols:
        raise ValueError(f"feature manifest missing columns: {missing_cols}")
    if manifest["feature"].duplicated().any():
        raise ValueError("feature manifest contains duplicate feature rows")

    detail_rows = []
    for _, m in manifest.iterrows():
        feature = m["feature"].strip()
        if feature not in candidates.columns:
            for cid in candidates[candidate_id]:
                detail_rows.append({candidate_id: cid, "feature": feature, "dimension": m["dimension"],
                                    "raw_value": "", "normalized_value": None,
                                    "evidence_state": "field_absent_from_candidate_schema",
                                    "feature_weight": m["feature_weight"], "reference_id": m["reference_id"]})
            continue
        weight = num(m["feature_weight"], f"feature_weight {feature}")
        if weight < 0:
            raise ValueError(f"negative feature weight for {feature}")
        for cid, raw in zip(candidates[candidate_id], candidates[feature]):
            z, state = normalize_value(raw, m)
            detail_rows.append({candidate_id: cid, "feature": feature, "dimension": m["dimension"],
                                "raw_value": raw, "normalized_value": z, "evidence_state": state,
                                "feature_weight": weight, "reference_id": m["reference_id"]})

    detail = pd.DataFrame(detail_rows)
    dimension_rows = []
    for (cid, dimension), g in detail.groupby([candidate_id, "dimension"], sort=False):
        expected = len(g)
        observed = g[g["evidence_state"].eq("observed")].copy()
        observed_n = len(observed)
        coverage = observed_n / expected if expected else 0.0
        if observed_n:
            w = pd.to_numeric(observed["feature_weight"], errors="raise")
            total_w = float(w.sum())
            value = None if total_w <= 0 else float((pd.to_numeric(observed["normalized_value"]) * w).sum() / total_w)
        else:
            value = None
        if coverage == 1:
            state = "complete"
        elif coverage > 0:
            state = "partial"
        else:
            state = "insufficient"
        dimension_rows.append({candidate_id: cid, "dimension": dimension, "dimension_value": value,
                               "observed_feature_count": observed_n, "expected_feature_count": expected,
                               "dimension_coverage_rate": coverage, "dimension_evidence_state": state})

    dimensions_long = pd.DataFrame(dimension_rows)
    values_wide = dimensions_long.pivot(index=candidate_id, columns="dimension", values="dimension_value").reset_index()
    coverage_wide = dimensions_long.pivot(index=candidate_id, columns="dimension", values="dimension_coverage_rate")
    coverage_wide.columns = [f"{c}__coverage" for c in coverage_wide.columns]
    coverage_wide = coverage_wide.reset_index()
    model_table = values_wide.merge(coverage_wide, on=candidate_id, how="left")

    summary = {
        "candidate_count": int(candidates[candidate_id].nunique()),
        "feature_count": int(manifest["feature"].nunique()),
        "dimension_count": int(manifest["dimension"].nunique()),
        "fully_observed_dimension_rows": int(dimensions_long["dimension_evidence_state"].eq("complete").sum()),
        "partial_dimension_rows": int(dimensions_long["dimension_evidence_state"].eq("partial").sum()),
        "insufficient_dimension_rows": int(dimensions_long["dimension_evidence_state"].eq("insufficient").sum()),
        "note": "Dimension coverage is evidence metadata and must not be used as desirability by default."
    }
    return detail, dimensions_long, model_table, summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--candidate-id", default="candidate_id")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    detail, dimensions, model, summary = build(read(args.candidates), read(args.manifest), args.candidate_id)
    detail.to_csv(args.out_dir / "candidate_normalized_feature_detail.csv", index=False)
    dimensions.to_csv(args.out_dir / "candidate_dimensions_long.csv", index=False)
    model.to_csv(args.out_dir / "candidate_dimension_model_table.csv", index=False)
    (args.out_dir / "candidate_dimension_normalization_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
