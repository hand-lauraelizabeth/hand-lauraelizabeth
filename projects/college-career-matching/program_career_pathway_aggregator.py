#!/usr/bin/env python3
"""Aggregate many-to-many program→occupation evidence without hiding pathway breadth.

The output preserves pathway-level records and creates descriptive program-level
summaries. It does not select a single 'best' occupation or create a recommendation score.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

SUPPRESS={"","NA","N/A","NULL","NONE","#","**","***","SUPPRESSED"}

def read(p): return pd.read_csv(p,dtype=str,keep_default_na=False)
def req(df,cols,label):
    m=[c for c in cols if c not in df.columns]
    if m: raise ValueError(f"{label} missing columns: {m}")
def num(s): return pd.to_numeric(s.mask(s.astype(str).str.strip().str.upper().isin(SUPPRESS)),errors="coerce")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--programs",type=Path,required=True,help="UNITID,program_id,cip_code")
    p.add_argument("--cip-soc",type=Path,required=True,help="cip_code,occ_code")
    p.add_argument("--occupation-evidence",type=Path,required=True,help="one row per occ_code with selected national/projection/O*NET measures")
    p.add_argument("--local-evidence",type=Path,help="optional candidate_id,occ_code local evidence")
    p.add_argument("--candidates",type=Path,help="optional candidate_id,UNITID,program_id")
    p.add_argument("--out-dir",type=Path,required=True)
    a=p.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
    programs=read(a.programs); req(programs,["UNITID","program_id","cip_code"],"programs")
    x=read(a.cip_soc); req(x,["cip_code","occ_code"],"CIP-SOC")
    occ=read(a.occupation_evidence); req(occ,["occ_code"],"occupation evidence")
    if occ["occ_code"].duplicated().any(): raise ValueError("occupation evidence must be unique by occ_code")
    paths=programs.merge(x,on="cip_code",how="left",validate="many_to_many",indicator="_path")
    paths["pathway_status"]=paths["_path"].map({"both":"mapped","left_only":"no_soc_mapping"}); paths=paths.drop(columns="_path")
    paths=paths.merge(occ,on="occ_code",how="left",validate="many_to_one",suffixes=("","_occ"))
    if a.candidates:
        c=read(a.candidates); req(c,["candidate_id","UNITID","program_id"],"candidates")
        paths=c[["candidate_id","UNITID","program_id"]].merge(paths,on=["UNITID","program_id"],how="left",validate="one_to_many")
    if a.local_evidence:
        if "candidate_id" not in paths.columns: raise ValueError("--local-evidence requires --candidates")
        loc=read(a.local_evidence); req(loc,["candidate_id","occ_code"],"local evidence")
        if loc[["candidate_id","occ_code"]].duplicated().any(): raise ValueError("local evidence duplicate candidate_id+occ_code")
        overlap=[c for c in loc.columns if c in paths.columns and c not in ["candidate_id","occ_code"]]
        if overlap: raise ValueError(f"local evidence would overwrite columns: {overlap}")
        paths=paths.merge(loc,on=["candidate_id","occ_code"],how="left",validate="many_to_one")
    key="candidate_id" if "candidate_id" in paths.columns else "program_id"
    numeric_cols=[]
    for c in paths.columns:
        if c in {"UNITID","program_id","cip_code","occ_code","candidate_id"}: continue
        converted=num(paths[c])
        if converted.notna().any(): paths[c+"__numeric"]=converted; numeric_cols.append(c+"__numeric")
    summaries=[]
    for k,g in paths.groupby(key,dropna=False,sort=False):
        mapped=g[g["pathway_status"]=="mapped"]
        row={key:k,"pathway_count":int(mapped["occ_code"].nunique()),"pathway_record_count":int(len(mapped)),
             "pathway_mapping_status":"mapped" if len(mapped) else "no_soc_mapping"}
        for c in numeric_cols:
            vals=mapped[c].dropna()
            stem=c.removesuffix("__numeric")
            row[f"{stem}__observed_n"]=int(vals.size)
            row[f"{stem}__coverage_rate"]=(float(vals.size)/len(mapped)) if len(mapped) else None
            # Median + range show central tendency and breadth; no max-only proxy.
            row[f"{stem}__median"]=float(vals.median()) if len(vals) else None
            row[f"{stem}__min"]=float(vals.min()) if len(vals) else None
            row[f"{stem}__max"]=float(vals.max()) if len(vals) else None
        summaries.append(row)
    summary=pd.DataFrame(summaries)
    paths.drop(columns=numeric_cols,errors="ignore").to_csv(a.out_dir/"program_career_pathway_evidence.csv",index=False)
    summary.to_csv(a.out_dir/"program_career_pathway_summary.csv",index=False)
    qa={"pathway_rows":int(len(paths)),"summary_rows":int(len(summary)),"numeric_measures_summarized":[c.removesuffix("__numeric") for c in numeric_cols],
        "rule":"Program summaries preserve pathway count, measure coverage, median, and range; they do not choose the highest-value occupation as the program value."}
    (a.out_dir/"program_career_pathway_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")

if __name__=="__main__": main()
