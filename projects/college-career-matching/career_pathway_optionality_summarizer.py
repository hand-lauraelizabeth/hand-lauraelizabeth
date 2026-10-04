#!/usr/bin/env python3
"""Summarize career-pathway alignment without collapsing optionality into one opaque score."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd


def read(p): return pd.read_csv(p,dtype=str,keep_default_na=False)
def req(df,cols,label):
    m=[c for c in cols if c not in df.columns]
    if m: raise ValueError(f"{label} missing columns: {m}")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--alignment",type=Path,required=True,help="career_pathway_alignment.csv")
    p.add_argument("--occupation-labels",type=Path,help="optional occ_code,occupation_title")
    p.add_argument("--threshold",type=float,help="validated strong-alignment threshold; omitted means no strong-pathway classification")
    p.add_argument("--representative-count",type=int,default=3)
    p.add_argument("--out-dir",type=Path,required=True)
    a=p.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
    df=read(a.alignment); req(df,["occ_code","career_alignment_score","career_alignment_coverage_rate","career_alignment_status"],"alignment")
    groupcols=[c for c in ["candidate_id","UNITID","program_id","cip_code"] if c in df.columns]
    if not groupcols: raise ValueError("alignment must contain candidate_id or program identity columns")
    df["score_num"]=pd.to_numeric(df["career_alignment_score"],errors="coerce")
    df["coverage_num"]=pd.to_numeric(df["career_alignment_coverage_rate"],errors="coerce")
    if a.occupation_labels:
        lab=read(a.occupation_labels); req(lab,["occ_code","occupation_title"],"occupation labels")
        if lab["occ_code"].duplicated().any(): raise ValueError("occupation labels duplicate occ_code")
        df=df.merge(lab,on="occ_code",how="left",validate="many_to_one")
    rows=[]; reps=[]
    for keys,g in df.groupby(groupcols,dropna=False,sort=False):
        if not isinstance(keys,tuple): keys=(keys,)
        row=dict(zip(groupcols,keys)); mapped=g[g["occ_code"].str.strip()!=""].copy(); observed=mapped[mapped["score_num"].notna()].copy()
        row["career_pathway_count"]=int(mapped["occ_code"].nunique())
        row["career_alignment_observed_pathways"]=int(observed["occ_code"].nunique())
        row["career_alignment_pathway_coverage_rate"]=(row["career_alignment_observed_pathways"]/row["career_pathway_count"]) if row["career_pathway_count"] else None
        row["career_alignment_median"]=float(observed["score_num"].median()) if len(observed) else None
        row["career_alignment_min"]=float(observed["score_num"].min()) if len(observed) else None
        row["career_alignment_max"]=float(observed["score_num"].max()) if len(observed) else None
        row["career_alignment_iqr"]=float(observed["score_num"].quantile(.75)-observed["score_num"].quantile(.25)) if len(observed)>=2 else None
        row["career_alignment_mean_preference_coverage"]=float(observed["coverage_num"].mean()) if len(observed) else None
        if a.threshold is not None:
            strong=observed[observed["score_num"]>=a.threshold]
            row["strong_alignment_pathway_count"]=int(strong["occ_code"].nunique())
            row["strong_alignment_pathway_share"]=(row["strong_alignment_pathway_count"]/row["career_alignment_observed_pathways"]) if row["career_alignment_observed_pathways"] else None
        else:
            row["strong_alignment_pathway_count"]=None; row["strong_alignment_pathway_share"]=None
        row["career_optionality_status"]="observed" if len(observed) else "insufficient_alignment_evidence"
        rows.append(row)
        # Representatives are explanatory examples, not an aggregation rule.
        if len(observed):
            sample=observed.sort_values(["score_num","coverage_num","occ_code"],ascending=[False,False,True]).head(max(a.representative_count,0))
            for rank,(_,r) in enumerate(sample.iterrows(),1):
                rr={c:row[c] for c in groupcols}; rr.update({"representative_rank":rank,"occ_code":r["occ_code"],"career_alignment_score":r["score_num"],"career_alignment_coverage_rate":r["coverage_num"]})
                if "occupation_title" in r.index: rr["occupation_title"]=r["occupation_title"]
                reps.append(rr)
    out=pd.DataFrame(rows); rep=pd.DataFrame(reps)
    out.to_csv(a.out_dir/"career_optionality_summary.csv",index=False)
    rep.to_csv(a.out_dir/"career_representative_pathways.csv",index=False)
    qa={"summary_rows":int(len(out)),"representative_rows":int(len(rep)),"strong_alignment_threshold":a.threshold,
        "rule":"Optionality is reported as pathway breadth, alignment distribution, and evidence coverage. Pathway count alone is not a quality score; representative pathways are examples, not proof of program-wide fit."}
    (a.out_dir/"career_optionality_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")

if __name__=="__main__": main()
