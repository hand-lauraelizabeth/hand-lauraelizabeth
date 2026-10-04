#!/usr/bin/env python3
"""Aggregate many-to-many program→occupation evidence without hiding pathway breadth."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
SUPPRESS={"","NA","N/A","NULL","NONE","#","**","***","SUPPRESSED"}
def read(p):return pd.read_csv(p,dtype=str,keep_default_na=False)
def req(df,cols,label):
 m=[c for c in cols if c not in df.columns]
 if m:raise ValueError(f"{label} missing columns: {m}")
def num(s):return pd.to_numeric(s.mask(s.astype(str).str.strip().str.upper().isin(SUPPRESS)),errors="coerce")
def main():
 p=argparse.ArgumentParser();p.add_argument("--programs",type=Path,required=True);p.add_argument("--cip-soc",type=Path,required=True);p.add_argument("--occupation-evidence",type=Path,required=True);p.add_argument("--local-evidence",type=Path);p.add_argument("--candidates",type=Path);p.add_argument("--out-dir",type=Path,required=True);a=p.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 programs=read(a.programs);req(programs,["UNITID","program_id","cip_code"],"programs")
 if programs[["UNITID","program_id"]].duplicated().any():raise ValueError("programs must be unique by UNITID+program_id")
 x=read(a.cip_soc);req(x,["cip_code","occ_code"],"CIP-SOC");occ=read(a.occupation_evidence);req(occ,["occ_code"],"occupation evidence")
 if occ["occ_code"].duplicated().any():raise ValueError("occupation evidence must be unique by occ_code")
 paths=programs.merge(x,on="cip_code",how="left",validate="many_to_many",indicator="_path");paths["pathway_status"]=paths["_path"].map({"both":"mapped","left_only":"no_soc_mapping"});paths=paths.drop(columns="_path").merge(occ,on="occ_code",how="left",validate="many_to_one",suffixes=("","_occ"))
 if a.candidates:
  c=read(a.candidates);req(c,["candidate_id","UNITID","program_id"],"candidates")
  if c["candidate_id"].duplicated().any():raise ValueError("candidates must be unique by candidate_id")
  paths=c[["candidate_id","UNITID","program_id"]].merge(paths,on=["UNITID","program_id"],how="left",validate="one_to_many")
 if a.local_evidence:
  if "candidate_id" not in paths:raise ValueError("--local-evidence requires --candidates")
  loc=read(a.local_evidence);req(loc,["candidate_id","occ_code"],"local evidence")
  if loc[["candidate_id","occ_code"]].duplicated().any():raise ValueError("local evidence duplicate candidate_id+occ_code")
  overlap=[c for c in loc if c in paths and c not in ["candidate_id","occ_code"]]
  if overlap:raise ValueError(f"local evidence would overwrite columns: {overlap}")
  paths=paths.merge(loc,on=["candidate_id","occ_code"],how="left",validate="many_to_one")
 groupcols=["candidate_id"] if "candidate_id" in paths else ["UNITID","program_id"]
 numeric=[]
 for c in list(paths.columns):
  if c in {"UNITID","program_id","cip_code","occ_code","candidate_id"}:continue
  converted=num(paths[c])
  if converted.notna().any():paths[c+"__numeric"]=converted;numeric.append(c+"__numeric")
 summaries=[]
 for keys,g in paths.groupby(groupcols,dropna=False,sort=False):
  if not isinstance(keys,tuple):keys=(keys,)
  row=dict(zip(groupcols,keys));mapped=g[g["pathway_status"]=="mapped"];row.update({"pathway_count":int(mapped["occ_code"].nunique()),"pathway_record_count":int(len(mapped)),"pathway_mapping_status":"mapped" if len(mapped) else "no_soc_mapping"})
  for c in numeric:
   vals=mapped[c].dropna();stem=c.removesuffix("__numeric");row[f"{stem}__observed_n"]=int(vals.size);row[f"{stem}__coverage_rate"]=(float(vals.size)/len(mapped)) if len(mapped) else None;row[f"{stem}__median"]=float(vals.median()) if len(vals) else None;row[f"{stem}__min"]=float(vals.min()) if len(vals) else None;row[f"{stem}__max"]=float(vals.max()) if len(vals) else None
  summaries.append(row)
 summary=pd.DataFrame(summaries);paths.drop(columns=numeric,errors="ignore").to_csv(a.out_dir/"program_career_pathway_evidence.csv",index=False);summary.to_csv(a.out_dir/"program_career_pathway_summary.csv",index=False)
 qa={"pathway_rows":int(len(paths)),"summary_rows":int(len(summary)),"summary_grain":"candidate_id" if "candidate_id" in paths else "UNITID+program_id","numeric_measures_summarized":[c.removesuffix("__numeric") for c in numeric],"rule":"Program summaries preserve institutional program identity and pathway breadth; they do not choose the highest-value occupation as program value."};(a.out_dir/"program_career_pathway_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
if __name__=="__main__":main()
