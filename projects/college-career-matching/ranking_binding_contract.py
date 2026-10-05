#!/usr/bin/env python3
"""Shared identity and validation helpers for review-eligible ranked service bundles."""
from __future__ import annotations
import copy,hashlib,json,math

def clean(v):return str(v).strip() if v is not None else ""

def ranking_context_id(request,data_version,model_version):
 r=copy.deepcopy(request)
 r.pop("page",None);r.pop("page_size",None)
 payload=json.dumps({"request":r,"data_version":data_version,"model_version":model_version},sort_keys=True,separators=(",",":"))
 return "rankctx_"+hashlib.sha256(payload.encode()).hexdigest()[:24]

def candidate_universe_sha256(candidate_ids):
 vals=[clean(x) for x in candidate_ids]
 if any(not x for x in vals):raise ValueError("candidate universe contains blank candidate_id")
 if len(vals)!=len(set(vals)):raise ValueError("candidate universe contains duplicate candidate_id")
 payload=json.dumps(sorted(vals),separators=(",",":"))
 return hashlib.sha256(payload.encode()).hexdigest()

def finite_number(v,label):
 try:x=float(v)
 except Exception as exc:raise ValueError(f"{label}: expected numeric value, got {v!r}") from exc
 if not math.isfinite(x):raise ValueError(f"{label}: value must be finite")
 return x

def validate_rankings(rankings,eligible_ids):
 eligible=set(eligible_ids);seen=set();parsed=[]
 for i,row in enumerate(rankings,1):
  cid=clean(row.get("candidate_id"))
  if not cid:raise ValueError(f"ranking row {i}: blank candidate_id")
  if cid in seen:raise ValueError(f"duplicate ranked candidate_id: {cid}")
  if cid not in eligible:raise ValueError(f"ranked candidate is outside bound eligible universe: {cid}")
  seen.add(cid)
  try:rank=int(clean(row.get("rank")))
  except Exception as exc:raise ValueError(f"{cid}: rank must be a positive integer") from exc
  if rank<1:raise ValueError(f"{cid}: rank must be >= 1")
  score=finite_number(row.get("baseline_score"),f"{cid} baseline_score")
  if not 0<=score<=1:raise ValueError(f"{cid}: baseline_score outside [0,1]")
  if clean(row.get("review_eligibility"))!="eligible_for_review":raise ValueError(f"{cid}: ranking is not review-eligible")
  parsed.append({"candidate_id":cid,"rank":rank,"baseline_score":score,"review_eligibility":"eligible_for_review"})
 # Recompute competition ranks from score to prevent stale/tampered rank labels.
 ordered=sorted(parsed,key=lambda r:(-r["baseline_score"],r["candidate_id"]))
 last=None;expected_rank=0
 for i,row in enumerate(ordered,1):
  if last is None or row["baseline_score"]!=last:expected_rank=i;last=row["baseline_score"]
  if row["rank"]!=expected_rank:raise ValueError(f"{row['candidate_id']}: rank does not match baseline score ordering")
 return ordered

def validate_bundle(bundle,request,data_version,model_version,eligible_ids):
 if bundle.get("schema_version")!="1.0":raise ValueError("ranking bundle: unsupported schema_version")
 if bundle.get("production_authorized") is not False:raise ValueError("ranking bundle must not claim production authorization")
 if bundle.get("review_eligible") is not True:raise ValueError("ranking bundle is not review-eligible")
 binding=bundle.get("binding")
 if not isinstance(binding,dict):raise ValueError("ranking bundle missing binding")
 expected_context=ranking_context_id(request,data_version,model_version)
 if clean(binding.get("ranking_context_id"))!=expected_context:raise ValueError("ranking bundle context does not match request/data/model identity")
 if clean(binding.get("data_version"))!=clean(data_version):raise ValueError("ranking bundle data_version mismatch")
 if clean(binding.get("model_version"))!=clean(model_version):raise ValueError("ranking bundle model_version mismatch")
 ids=list(eligible_ids);digest=candidate_universe_sha256(ids)
 if clean(binding.get("eligible_candidate_universe_sha256"))!=digest:raise ValueError("ranking bundle eligible candidate universe mismatch")
 try:count=int(binding.get("eligible_candidate_count"))
 except Exception as exc:raise ValueError("ranking bundle eligible_candidate_count invalid") from exc
 if count!=len(ids):raise ValueError("ranking bundle eligible_candidate_count mismatch")
 rankings=bundle.get("rankings")
 if not isinstance(rankings,list):raise ValueError("ranking bundle rankings must be an array")
 parsed=validate_rankings(rankings,ids)
 try:ranked_count=int(binding.get("ranked_candidate_count"))
 except Exception as exc:raise ValueError("ranking bundle ranked_candidate_count invalid") from exc
 if ranked_count!=len(parsed):raise ValueError("ranking bundle ranked_candidate_count mismatch")
 return {r["candidate_id"]:r for r in parsed}
