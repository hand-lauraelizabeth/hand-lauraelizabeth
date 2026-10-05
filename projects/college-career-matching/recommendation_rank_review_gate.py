#!/usr/bin/env python3
"""Gate baseline ranked results behind the recommendation release decision.

A ranking can exist for validation while remaining ineligible for review. This
adapter never creates production authorization; it only distinguishes blocked
rankings from rankings whose declared recommendation gate passed.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

def clean(v):return str(v).strip() if v is not None else ""

def read_csv(path):
 with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))

def build(ranked,ranking_summary,release_decision):
 decision=clean(release_decision.get("release_decision"))
 ranking_status=clean(ranking_summary.get("status"))
 if decision=="ELIGIBLE_FOR_REVIEW" and ranking_status=="RANKING_READY_FOR_VALIDATION":
  out=[]
  for row in ranked:
   x=dict(row);x["review_eligibility"]="eligible_for_review";out.append(x)
  status="RANKED_RESULTS_ELIGIBLE_FOR_REVIEW"
 else:
  out=[];status="RANKED_RESULTS_BLOCKED_FROM_REVIEW"
 summary={
  "status":status,
  "recommendation_release_decision":decision or "MISSING",
  "ranking_status":ranking_status or "MISSING",
  "ranked_input_count":len(ranked),
  "review_eligible_ranked_count":len(out),
  "production_authorized":False,
  "rules":[
   "A calculated ranking is not review-eligible unless the recommendation release gate says ELIGIBLE_FOR_REVIEW.",
   "BLOCKED, missing, or unknown release decisions expose zero review-eligible ranked rows.",
   "ELIGIBLE_FOR_REVIEW is not production authorization."
  ]
 }
 return out,summary

def write_csv(path,rows):
 cols=["candidate_id","ranking_status","baseline_score","rank","missing_weighted_dimensions","partial_weighted_dimensions","weighted_dimension_count","review_eligibility"]
 with Path(path).open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--ranked",type=Path,required=True);ap.add_argument("--ranking-summary",type=Path,required=True);ap.add_argument("--release-decision",type=Path,required=True);ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 ranked=read_csv(a.ranked);ranking_summary=json.loads(a.ranking_summary.read_text(encoding="utf-8"));release=json.loads(a.release_decision.read_text(encoding="utf-8"));rows,summary=build(ranked,ranking_summary,release)
 write_csv(a.out_dir/"review_eligible_ranked_candidates.csv",rows);(a.out_dir/"ranked_result_review_eligibility.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

if __name__=="__main__":main()
