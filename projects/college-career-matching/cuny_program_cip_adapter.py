#!/usr/bin/env python3
"""Conservative CUNY T-Rex program -> registered-program/CIP crosswalk.

Never infers CIP from title similarity alone. Exact authoritative program IDs are
preferred; otherwise rows are retained for review. Intended inputs are a T-Rex
program inventory export and an authoritative CUNY/NYSED program inventory.
"""
from __future__ import annotations
import argparse, csv, hashlib, re
from pathlib import Path


def norm(v):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (v or "").lower()).split())

def read(path):
    with path.open(newline="", encoding="utf-8-sig") as f: return list(csv.DictReader(f))

def first(r, names):
    for n in names:
        if str(r.get(n, "")).strip(): return str(r[n]).strip()
    return ""

def sid(*parts):
    return hashlib.sha256("|".join(norm(x) for x in parts).encode()).hexdigest()[:16]

def main():
    p=argparse.ArgumentParser(); p.add_argument("--trex-programs",type=Path,required=True); p.add_argument("--registered-programs",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--review",type=Path,required=True)
    a=p.parse_args(); trex=read(a.trex_programs); reg=read(a.registered_programs)
    by_id={}
    for r in reg:
        rid=first(r,["program_id","irp_code","IRP","program_code","Program Code"])
        if rid: by_id.setdefault(norm(rid),[]).append(r)
    out=[]
    for t in trex:
        college=first(t,["college","college_name","institution"]); name=first(t,["program_name","plan_name","plan","major"]); award=first(t,["award","degree","degree_type"]); rid=first(t,["registered_program_id","irp_code","program_code"])
        cand=by_id.get(norm(rid),[]) if rid else []
        status="accepted" if len(cand)==1 else ("review" if cand else "unresolved")
        r=cand[0] if len(cand)==1 else {}
        out.append({"program_crosswalk_id":"CUNY-PROG-"+sid(college,name,award,rid),"trex_college":college,"trex_program_name":name,"trex_award":award,"trex_program_id":first(t,["trex_program_id","plan_id","program_id"]),"registered_program_id":rid or first(r,["program_id","irp_code","IRP","program_code","Program Code"]),"cip_code":first(r,["cip","cip_code","CIP","CIP Code"]),"hegis_code":first(r,["hegis","hegis_code","HEGIS"]),"match_method":"authoritative_program_id" if len(cand)==1 else "none","match_status":status,"candidate_count":len(cand),"review_note":"" if status=="accepted" else "Do not infer CIP from title similarity; reconcile against authoritative registered-program evidence."})
    fields=list(out[0]) if out else ["program_crosswalk_id","trex_college","trex_program_name","trex_award","trex_program_id","registered_program_id","cip_code","hegis_code","match_method","match_status","candidate_count","review_note"]
    for path,rows in [(a.output,out),(a.review,[r for r in out if r["match_status"]!="accepted"])]:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("w",newline="",encoding="utf-8") as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    if any(r["match_status"]=="accepted" and not r["cip_code"] for r in out): raise SystemExit("QA FAIL: accepted registered-program match lacks CIP")
    print(f"CUNY program crosswalk: {sum(r['match_status']=='accepted' for r in out)}/{len(out)} accepted")
if __name__=="__main__": main()
