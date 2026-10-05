#!/usr/bin/env python3
"""Assemble product-facing labor evidence for a candidate and requested work market."""
from __future__ import annotations
from collections import defaultdict
def clean(v):return str(v).strip() if v is not None else ""
def index(rows):
 out=defaultdict(list)
 for r in rows:
  key=(clean(r.get("UNITID")),clean(r.get("program_id")))
  if not all(key):raise ValueError("labor evidence requires UNITID and program_id")
  out[key].append(r)
 return out
def build_for_candidate(candidate,current_rows,projection_rows,work_market=None):
 key=(clean(candidate.get("UNITID")),clean(candidate.get("program_id")));current=index(current_rows).get(key,[]);future=index(projection_rows).get(key,[])
 selected=[]
 if work_market:
  mid=clean(work_market.get("market_id"));mtype=clean(work_market.get("market_type"))
  selected=[r for r in current if clean(r.get("market_id"))==mid and (not mtype or clean(r.get("market_type"))==mtype)]
 return {"selected_work_market":{"market_id":clean(work_market.get("market_id")) if work_market else None,"market_type":clean(work_market.get("market_type")) if work_market else None,"evidence_state":"observed" if selected else ("not_requested" if not work_market else "unavailable"),"soc_evidence":[{"soc_code":clean(r.get("soc_code")),"employment":r.get("employment"),"employment_state":r.get("employment_state","missing"),"median_wage":r.get("median_wage"),"wage_state":r.get("wage_state","missing"),"source_vintage":r.get("source_vintage")} for r in selected]},"long_term_outlook":{"evidence_state":"observed" if future else "unavailable","soc_evidence":[{"soc_code":clean(r.get("soc_code")),"projection_geography":r.get("projection_geography"),"base_year":r.get("base_year"),"projection_year":r.get("projection_year"),"employment_change_pct":r.get("employment_change_pct"),"annual_openings":r.get("annual_openings"),"source_vintage":r.get("source_vintage")} for r in future]},"semantic_note":"Current selected-market evidence and long-term outlook are separate evidence families; neither substitutes for the other."}
