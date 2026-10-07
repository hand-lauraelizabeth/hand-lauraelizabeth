#!/usr/bin/env python3
"""Run the current SUNY transfer evidence chain against a current IPEDS directory.

This produces an observed transfer identity baseline without forcing unresolved
institution names into IPEDS UNITIDs.

Pipeline:
1. capture authoritative SUNY STEP HTML table;
2. normalize agreement direction/program fields;
3. build unique campus-label rows from both sides of agreements;
4. resolve only evidence-qualified campus identities against current IPEDS;
5. join accepted identity evidence back to agreements;
6. emit one baseline JSON summary.

Program/CIP mapping remains a later reviewed stage.
"""
from __future__ import annotations
import argparse,csv,json,re,unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from suny_step_live_snapshot import run as snapshot_run
from suny_transfer_agreement_adapter import run as agreement_run
from suny_institution_identity import build_indexes,resolve,read_csv,write_csv
from suny_transfer_identity_bridge import run as bridge_run

SOURCE_URL="https://step.transfer.suny.edu/agreements/"

IDENTITY_FIELDS=[
 "campus_source_id","campus_name_source","identity_class",
 "parent_label_for_matching","subunit_label","unitid","ipeds_name",
 "match_method","match_status","candidate_count","source_url","review_note",
]

def campus_rows(agreements):
 seen=set();rows=[]
 for a in agreements:
  for col in ("sending_institution_source_id","receiving_institution_source_id"):
   label=(a.get(col) or "").strip()
   key=label.casefold()
   if label and key not in seen:
    seen.add(key);rows.append({"campus_source_id":label,"campus_name":label,"source_url":SOURCE_URL})
 return rows

def _norm(value):
 value=unicodedata.normalize("NFKD",str(value or ""))
 value="".join(ch for ch in value if not unicodedata.combining(ch)).lower()
 return " ".join(re.sub(r"[^a-z0-9]+"," ",value).split())

def diagnostic_candidates(label,ipeds_rows,limit=5):
 q=_norm(label);qt=set(q.split());scored=[]
 for row in ipeds_rows:
  if (row.get("STABBR") or "").strip().upper()!="NY": continue
  name=(row.get("INSTNM") or "").strip();n=_norm(name);nt=set(n.split())
  if not n: continue
  seq=SequenceMatcher(None,q,n).ratio()
  jac=len(qt&nt)/len(qt|nt) if qt|nt else 0
  contains=1.0 if q and (q in n or n in q) else 0.0
  score=.55*seq+.30*jac+.15*contains
  scored.append((score,row.get("UNITID",""),name))
 return [{"score":round(s,4),"unitid":u,"ipeds_name":n} for s,u,n in sorted(scored,reverse=True)[:limit]]

def identity_stage(campuses,ipeds_rows,out_dir):
 _,exact,token=build_indexes(ipeds_rows)
 results=[resolve(r,exact,token) for r in campuses]
 write_csv(out_dir/"suny_institution_identity.csv",results,IDENTITY_FIELDS)
 write_csv(out_dir/"suny_institution_identity_review.csv",[r for r in results if r["match_status"] in {"review","unresolved"}],IDENTITY_FIELDS)
 total=len(results);matchable=sum(r["match_status"]!="not_applicable" for r in results)
 accepted=sum(r["match_status"]=="accepted" for r in results)
 review=sum(r["match_status"]=="review" for r in results)
 unresolved=sum(r["match_status"]=="unresolved" for r in results)
 na=sum(r["match_status"]=="not_applicable" for r in results)
 coverage={
  "source_campus_labels":total,
  "matchable_labels":matchable,
  "accepted_matches":accepted,
  "review_candidates":review,
  "unresolved":unresolved,
  "group_not_applicable":na,
  "accepted_match_rate_of_matchable":round(accepted/matchable,6) if matchable else 0,
  "accepted_details":[
   {"source_label":r["campus_name_source"],"unitid":r["unitid"],"ipeds_name":r["ipeds_name"],"match_method":r["match_method"]}
   for r in results if r["match_status"]=="accepted"
  ],
  "review_candidate_details":[
   {"source_label":r["campus_name_source"],"candidate_ipeds_name":r["ipeds_name"],"match_method":r["match_method"],"candidate_count":r["candidate_count"],"review_note":r["review_note"]}
   for r in results if r["match_status"]=="review"
  ],
  "unresolved_labels":[r["campus_name_source"] for r in results if r["match_status"]=="unresolved"],
  "diagnostic_candidates":{
   r["campus_name_source"]:diagnostic_candidates(r["campus_name_source"],ipeds_rows)
   for r in results if r["match_status"] in {"review","unresolved"}
  },
 }
 with (out_dir/"suny_institution_identity_coverage.json").open("w",encoding="utf-8") as f:
  json.dump(coverage,f,indent=2,sort_keys=True);f.write("\n")
 return coverage

def run(ipeds_hd:Path,out_dir:Path):
 out_dir.mkdir(parents=True,exist_ok=True)
 raw=out_dir/"suny_step_raw.csv"
 snapshot_meta=snapshot_run(raw,out_dir/"suny_step_snapshot.html")
 normalized=out_dir/"transfer_agreement_suny.csv"
 agreement_qa=agreement_run(raw,normalized,out_dir/"transfer_agreement_suny_qa.json",retrieved_at=snapshot_meta["retrieved_at"])
 agreements=read_csv(normalized)
 campuses=campus_rows(agreements)
 write_csv(out_dir/"suny_transfer_campuses.csv",campuses,["campus_source_id","campus_name","source_url"])
 ipeds=read_csv(ipeds_hd)
 identity_coverage=identity_stage(campuses,ipeds,out_dir)
 bridge_qa=bridge_run(normalized,out_dir/"suny_institution_identity.csv",out_dir/"transfer_agreement_suny_identity.csv",out_dir/"transfer_agreement_suny_identity_qa.json")
 baseline={
  "status":"PASS" if agreement_qa["status"]=="PASS" and bridge_qa["status"]=="PASS" else "FAIL",
  "snapshot":snapshot_meta,
  "agreement_qa":agreement_qa,
  "identity_coverage":identity_coverage,
  "bridge_qa":bridge_qa,
  "guardrail":"Identity coverage is descriptive evidence availability, not transfer quality or fit. Program/CIP mapping remains unscored and unresolved.",
 }
 (out_dir/"suny_transfer_live_baseline.json").write_text(json.dumps(baseline,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 return baseline

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--ipeds-hd",required=True,type=Path)
 ap.add_argument("--output-dir",required=True,type=Path)
 a=ap.parse_args()
 baseline=run(a.ipeds_hd,a.output_dir)
 print(json.dumps(baseline,indent=2,sort_keys=True))
 raise SystemExit(0 if baseline["status"]=="PASS" else 1)
if __name__=="__main__":main()
