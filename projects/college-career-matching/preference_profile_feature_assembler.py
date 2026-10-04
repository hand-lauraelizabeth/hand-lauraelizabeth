#!/usr/bin/env python3
"""Assemble model-ready candidate features from explicit preferences and evidence.

No preference is invented when the profile is silent. Evidence is joined only at
its declared grain and duplicate joins fail rather than multiplying candidates.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd


def read(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def req(df, cols, label):
    miss=[c for c in cols if c not in df.columns]
    if miss: raise ValueError(f"{label} missing columns: {miss}")


def truthy(v): return str(v).strip().lower() in {"1","true","yes","y"}


def profile_contract(profile: pd.DataFrame) -> pd.DataFrame:
    req(profile,["preference_id","dimension","value","mode","priority_explicit"],"profile")
    if profile["preference_id"].duplicated().any(): raise ValueError("duplicate preference_id")
    allowed={"preference","hard_constraint","context"}
    bad=set(profile["mode"].str.strip().str.lower())-allowed
    if bad: raise ValueError(f"unsupported profile modes: {sorted(bad)}")
    # Silent/non-explicit rows are retained for audit but cannot influence model features.
    profile=profile.copy()
    profile["active_for_model"]=profile["priority_explicit"].map(truthy)
    return profile


def join_table(base: pd.DataFrame, table: pd.DataFrame, grain: str, label: str) -> pd.DataFrame:
    grains={
        "institution":["UNITID"],
        "program":["UNITID","program_id"],
        "candidate":["candidate_id"],
        "transfer_path":["UNITID","program_id","transfer_path_id"],
    }
    if grain not in grains: raise ValueError(f"unsupported grain {grain} for {label}")
    keys=grains[grain]
    req(base,keys,"candidate universe"); req(table,keys,label)
    if table[keys].duplicated().any(): raise ValueError(f"{label} not unique at declared {grain} grain")
    overlap=[c for c in table.columns if c in base.columns and c not in keys]
    if overlap: raise ValueError(f"{label} would overwrite existing columns: {overlap}")
    return base.merge(table,on=keys,how="left",validate="many_to_one")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--candidates",type=Path,required=True)
    p.add_argument("--profile",type=Path,required=True)
    p.add_argument("--source-manifest",type=Path,required=True,
                   help="CSV: source_id,path,grain,required")
    p.add_argument("--out-dir",type=Path,required=True)
    a=p.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
    candidates=read(a.candidates); req(candidates,["candidate_id","UNITID","program_id"],"candidates")
    if candidates["candidate_id"].duplicated().any(): raise ValueError("duplicate candidate_id")
    profile=profile_contract(read(a.profile))
    manifest=read(a.source_manifest); req(manifest,["source_id","path","grain","required"],"source manifest")
    assembled=candidates.copy(); join_log=[]
    for r in manifest.itertuples(index=False):
        path=Path(r.path)
        if not path.exists():
            if truthy(r.required): raise FileNotFoundError(f"required source missing: {r.source_id}: {path}")
            join_log.append({"source_id":r.source_id,"grain":r.grain,"status":"optional_source_missing"}); continue
        before=len(assembled); assembled=join_table(assembled,read(path),r.grain,r.source_id)
        if len(assembled)!=before: raise RuntimeError(f"{r.source_id} changed candidate row count")
        join_log.append({"source_id":r.source_id,"grain":r.grain,"status":"joined"})
    # Export active preferences separately: downstream scoring must consume only explicit priorities.
    active=profile[profile["active_for_model"]].copy()
    inactive=profile[~profile["active_for_model"]].copy()
    assembled.to_csv(a.out_dir/"model_ready_candidate_features.csv",index=False)
    active.to_csv(a.out_dir/"active_preference_profile.csv",index=False)
    inactive.to_csv(a.out_dir/"inactive_unspecified_profile_rows.csv",index=False)
    pd.DataFrame(join_log).to_csv(a.out_dir/"candidate_feature_join_log.csv",index=False)
    summary={"candidate_count":int(len(assembled)),"active_preference_count":int(len(active)),
             "inactive_profile_row_count":int(len(inactive)),"source_count":int(len(manifest)),
             "rule":"Only explicitly stated priorities may influence recommendation features or weights."}
    (a.out_dir/"candidate_feature_assembly_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

if __name__=="__main__": main()
