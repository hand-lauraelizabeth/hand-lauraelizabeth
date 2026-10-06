#!/usr/bin/env python3
"""Bridge labor evidence to candidate grain without conflating geography or horizon.

Current/local OEWS-style evidence and long-term BLS projections remain separate.
Candidate-program evidence is expanded through governed SOC pathways only.
"""
from __future__ import annotations
import argparse,csv
from collections import defaultdict
from pathlib import Path
def clean(v):return str(v).strip() if v is not None else ""
def read(p):
 with Path(p).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def write(p,rows):
 if not rows:return
 cols=[]
 for r in rows:
  for k in r:
   if k not in cols:cols.append(k)
 with p.open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def pathway_index(rows):
 out=defaultdict(set)
 for r in rows:
  key=(clean(r.get("UNITID")),clean(r.get("program_id")));soc=clean(r.get("soc_code"))
  if not all(key) or not soc:raise ValueError("career pathway rows require UNITID, program_id, soc_code")
  out[key].add(soc)
 return out
def current_local(pathways,rows):
 idx=defaultdict(list)
 for r in rows:
  soc=clean(r.get("soc_code"));market=clean(r.get("market_id"));market_type=clean(r.get("market_type"))
  if not soc or not market or not market_type:raise ValueError("current labor requires soc_code, market_id, market_type")
  idx[soc].append(r)
 out=[]
 for key,socs in pathway_index(pathways).items():
  for soc in sorted(socs):
   for r in idx.get(soc,[]):
    out.append({"UNITID":key[0],"program_id":key[1],"soc_code":soc,"occupation_title":clean(r.get("occupation_title") or r.get("occ_title") or r.get("soc_title")),"market_id":clean(r["market_id"]),"market_type":clean(r["market_type"]),"market_label":clean(r.get("market_label") or r.get("market_title") or r.get("area_title") or r.get("AREA_TITLE")),"employment":clean(r.get("employment")),"median_wage":clean(r.get("median_wage")),"employment_state":clean(r.get("employment_state")) or ("observed" if clean(r.get("employment")) else "missing"),"wage_state":clean(r.get("wage_state")) or ("observed" if clean(r.get("median_wage")) else "missing"),"source_vintage":clean(r.get("source_vintage"))})
 return out
def long_term(pathways,rows):
 idx={}
 for r in rows:
  soc=clean(r.get("soc_code"))
  if not soc:raise ValueError("projection rows require soc_code")
  if soc in idx:raise ValueError(f"duplicate projection SOC {soc}")
  idx[soc]=r
 out=[]
 for key,socs in pathway_index(pathways).items():
  for soc in sorted(socs):
   r=idx.get(soc)
   if r:out.append({"UNITID":key[0],"program_id":key[1],"soc_code":soc,"occupation_title":clean(r.get("occupation_title") or r.get("occ_title") or r.get("soc_title")),"projection_geography":clean(r.get("projection_geography")) or "national","base_year":clean(r.get("base_year")),"projection_year":clean(r.get("projection_year")),"employment_change_pct":clean(r.get("employment_change_pct")),"annual_openings":clean(r.get("annual_openings")),"source_vintage":clean(r.get("source_vintage"))})
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--pathways",type=Path,required=True);ap.add_argument("--current-local",type=Path);ap.add_argument("--projections",type=Path);ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True);p=read(a.pathways)
 if a.current_local:write(a.out_dir/"candidate_current_local_labor.csv",current_local(p,read(a.current_local)))
 if a.projections:write(a.out_dir/"candidate_long_term_outlook.csv",long_term(p,read(a.projections)))
if __name__=="__main__":main()
