#!/usr/bin/env python3
"""Normalize governed transfer and career outputs to product candidate grain.

This bridge summarizes evidence; it does not infer transfer guarantees, career
probabilities, or missing negative evidence.
"""
from __future__ import annotations
import csv,argparse
from collections import defaultdict
from pathlib import Path
def clean(v):return str(v).strip() if v is not None else ""
def read(p):
 with Path(p).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def summarize(rows,family):
 groups=defaultdict(list)
 for r in rows:
  key=(clean(r.get("UNITID")),clean(r.get("program_id")))
  if not all(key):raise ValueError(f"{family}: governed UNITID and program_id required")
  groups[key].append(r)
 out=[]
 for (uid,pid),rs in groups.items():
  x={"UNITID":uid,"program_id":pid,"evidence_record_count":str(len(rs))}
  if family=="transfer":
   x["evidence_levels"]=" | ".join(sorted({clean(r.get("evidence_level")) for r in rs if clean(r.get("evidence_level"))}));x["source_systems"]=" | ".join(sorted({clean(r.get("source_system")) for r in rs if clean(r.get("source_system"))}));x["transfer_evidence_present"]="1"
  elif family=="career":
   socs=sorted({clean(r.get("soc_code")) for r in rs if clean(r.get("soc_code"))});x["soc_count"]=str(len(socs));x["soc_codes"]=" | ".join(socs);x["career_pathway_evidence_present"]="1"
  else:raise ValueError(f"unsupported family {family}")
  out.append(x)
 return sorted(out,key=lambda r:(r["UNITID"],r["program_id"]))
def write(path,rows):
 if not rows:return
 with path.open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--transfer",type=Path);ap.add_argument("--career",type=Path);ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 if a.transfer:write(a.out_dir/"transfer_product_enrichment.csv",summarize(read(a.transfer),"transfer"))
 if a.career:write(a.out_dir/"career_product_enrichment.csv",summarize(read(a.career),"career"))
if __name__=="__main__":main()
