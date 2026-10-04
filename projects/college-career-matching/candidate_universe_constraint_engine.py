#!/usr/bin/env python3
"""Build and evaluate the recommendation candidate universe.

Primary grain: institution x program, optionally x transfer-path variant.
Hard constraints are evaluated as pass/fail/unknown/not_applicable. Unknown never
silently becomes fail. Excluded candidates are retained with reasons.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd

UNKNOWN = {"", "NA", "N/A", "NULL", "NONE", "UNKNOWN", "SUPPRESSED", "UNRESOLVED_IDENTITY", "SOURCE_NOT_COVERED", "NOT_PRE_EVALUATED"}


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def require(df: pd.DataFrame, cols: list[str], label: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{label} missing columns: {missing}")


def is_unknown(v: str) -> bool:
    return str(v).strip().upper() in UNKNOWN


def compare(value: str, operator: str, target: str) -> str:
    if is_unknown(value):
        return "unknown"
    op = operator.strip().lower()
    if op == "not_applicable":
        return "not_applicable"
    if op in {"eq", "neq", "in", "not_in"}:
        v = str(value).strip()
        vals = [x.strip() for x in str(target).split("|")]
        if op == "eq": return "pass" if v == str(target).strip() else "fail"
        if op == "neq": return "pass" if v != str(target).strip() else "fail"
        if op == "in": return "pass" if v in vals else "fail"
        return "pass" if v not in vals else "fail"
    try:
        v, t = float(value), float(target)
    except ValueError:
        return "unknown"
    tests = {
        "gte": v >= t, "gt": v > t, "lte": v <= t, "lt": v < t,
    }
    if op not in tests:
        raise ValueError(f"unsupported operator: {operator}")
    return "pass" if tests[op] else "fail"


def build_universe(institutions: pd.DataFrame, programs: pd.DataFrame, transfer: pd.DataFrame | None) -> pd.DataFrame:
    require(institutions, ["UNITID"], "institutions")
    require(programs, ["UNITID", "program_id"], "programs")
    if institutions["UNITID"].duplicated().any():
        raise ValueError("institution input must be unique by UNITID")
    if programs[["UNITID", "program_id"]].duplicated().any():
        raise ValueError("program input must be unique by UNITID + program_id")
    base = programs.merge(institutions, on="UNITID", how="left", validate="many_to_one", indicator="_institution_join")
    base["institution_identity_status"] = base["_institution_join"].map({"both":"resolved", "left_only":"unresolved"})
    base = base.drop(columns=["_institution_join"])
    base["transfer_path_id"] = ""
    if transfer is not None:
        require(transfer, ["UNITID", "program_id", "transfer_path_id"], "transfer paths")
        if transfer[["UNITID", "program_id", "transfer_path_id"]].duplicated().any():
            raise ValueError("transfer-path input contains duplicate variants")
        # Keep the ordinary institution-program candidate and add materially distinct path variants.
        variants = base.drop(columns=["transfer_path_id"]).merge(transfer, on=["UNITID", "program_id"], how="inner", validate="one_to_many")
        base = pd.concat([base, variants], ignore_index=True, sort=False)
    base["candidate_id"] = base.apply(lambda r: f"{r['UNITID']}::{r['program_id']}" + (f"::{r['transfer_path_id']}" if str(r.get('transfer_path_id','')).strip() else ""), axis=1)
    if base["candidate_id"].duplicated().any():
        raise ValueError("candidate construction produced duplicate candidate IDs")
    return base


def apply_constraints(universe: pd.DataFrame, constraints: pd.DataFrame):
    require(constraints, ["constraint_id", "field", "operator", "target", "unknown_policy"], "constraints")
    if constraints["constraint_id"].duplicated().any():
        raise ValueError("constraint IDs must be unique")
    rows = []
    for _, c in constraints.iterrows():
        field = c["field"].strip()
        for _, cand in universe.iterrows():
            status = "unknown" if field not in universe.columns else compare(cand[field], c["operator"], c["target"])
            rows.append({"candidate_id": cand["candidate_id"], "constraint_id": c["constraint_id"], "field": field,
                         "operator": c["operator"], "target": c["target"], "status": status,
                         "unknown_policy": c["unknown_policy"]})
    detail = pd.DataFrame(rows)

    def disposition(group: pd.DataFrame) -> str:
        if (group["status"] == "fail").any(): return "excluded"
        unknowns = group[group["status"] == "unknown"]
        if not unknowns.empty:
            policies = set(unknowns["unknown_policy"].str.strip().str.lower())
            if "exclude" in policies: return "excluded_unknown_by_explicit_policy"
            if "review" in policies: return "review"
            return "eligible_with_unknown"
        return "eligible"

    summary = detail.groupby("candidate_id", sort=False).apply(disposition, include_groups=False).rename("candidate_disposition").reset_index()
    failed = detail[detail["status"].isin(["fail", "unknown"])].groupby("candidate_id").apply(
        lambda g: " | ".join(f"{r.constraint_id}:{r.status}" for r in g.itertuples()), include_groups=False
    ).rename("constraint_notes").reset_index()
    out = universe.merge(summary, on="candidate_id", how="left").merge(failed, on="candidate_id", how="left")
    out["constraint_notes"] = out["constraint_notes"].fillna("")
    return out, detail


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--institutions", type=Path, required=True)
    p.add_argument("--programs", type=Path, required=True)
    p.add_argument("--constraints", type=Path, required=True)
    p.add_argument("--transfer-paths", type=Path)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    universe = build_universe(read(args.institutions), read(args.programs), read(args.transfer_paths) if args.transfer_paths else None)
    evaluated, detail = apply_constraints(universe, read(args.constraints))
    evaluated.to_csv(args.out_dir / "candidate_universe_evaluated.csv", index=False)
    detail.to_csv(args.out_dir / "candidate_constraint_detail.csv", index=False)
    counts = evaluated["candidate_disposition"].value_counts().to_dict()
    summary = {"candidate_count": int(len(evaluated)), "dispositions": {str(k): int(v) for k,v in counts.items()},
               "rule": "Unknown evidence is preserved unless an explicit constraint policy says otherwise."}
    (args.out_dir / "candidate_universe_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
