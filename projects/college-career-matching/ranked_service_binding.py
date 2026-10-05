#!/usr/bin/env python3
"""Bind gated review-eligible rankings to exact decision/data/model/candidate identity."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from match_service_adapter import validate_request,disposition
from ranking_binding_contract import ranking_context_id,candidate_universe_sha256,validate_rankings

def clean(v):return str(v).strip() if v is not None else ""

def read_csv(path):
 with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))

def eligible_candidate_ids(request,candidates):
 validate_request(request);ids=[];seen=set()
 for i,c in enumerate(candidates,1):
  cid=clean(c.get("candidate_id"))
  if not cid:raise ValueError(f"candidate row {i}: blank candidate_id")
  if cid in seen:raise ValueError(f"duplicate candidate_id: {cid}")
  seen.add(cid)
  status,_=disposition(c,request["constraints"])
  if status!="excluded":ids.append(cid)
 return sorted(ids)

def build(request,candidates,ranked,review_summary,data_version,model_version):
 if clean(review_summary.get("status"))!="RANKED_RESULTS_ELIGIBLE_FOR_REVIEW":raise ValueError("review summary does not authorize review-eligible ranked rows")
 if review_summary.get("production_authorized") is not False:raise ValueError("review summary must not claim production authorization")
 eligible=eligible_candidate_ids(request,candidates)
 parsed=validate_rankings(ranked,eligible)
 if int(review_summary.get("review_eligible_ranked_count",-1))!=len(parsed):raise ValueError("review summary ranked count mismatch")
 context=ranking_context_id(request,data_version,model_version)
 bundle={
  "schema_version":"1.0",
  "review_eligible":True,
  "production_authorized":False,
  "binding":{
   "ranking_context_id":context,
   "data_version":clean(data_version),
   "model_version":clean(model_version),
   "eligible_candidate_universe_sha256":candidate_universe_sha256(eligible),
   "eligible_candidate_count":len(eligible),
   "ranked_candidate_count":len(parsed),
  },
  "rankings":[parsed[cid] for cid in sorted(parsed,key=lambda x:(parsed[x]["rank"],x))],
  "semantic_rules":[
   "page and page_size are transport controls and are excluded from ranking_context_id; all decision semantics remain bound.",
   "A change to constraints, preferences, career preferences, geography, data_version, model_version, or eligible candidate universe invalidates this bundle.",
   "Only review-eligible ranked rows are included.",
   "Production authorization is always false."
  ]
 }
 return bundle

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--request",type=Path,required=True);ap.add_argument("--candidates",type=Path,required=True);ap.add_argument("--ranked",type=Path,required=True);ap.add_argument("--review-summary",type=Path,required=True);ap.add_argument("--data-version",required=True);ap.add_argument("--model-version",required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
 request=json.loads(a.request.read_text(encoding="utf-8"));candidates=json.loads(a.candidates.read_text(encoding="utf-8"));ranked=read_csv(a.ranked);summary=json.loads(a.review_summary.read_text(encoding="utf-8"));bundle=build(request,candidates,ranked,summary,a.data_version,a.model_version);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(bundle,indent=2),encoding="utf-8")

if __name__=="__main__":main()
