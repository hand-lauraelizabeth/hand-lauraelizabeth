#!/usr/bin/env python3
"""Normalize product-facing career-pathway evidence without inventing labels or ranking pathways."""
from __future__ import annotations
import json

def clean(v):return str(v).strip() if v is not None else ""

def _parsed(value):
 if value in (None,""):return []
 if isinstance(value,list):return value
 if isinstance(value,(tuple,set)):return list(value)
 text=clean(value)
 if text.startswith("["):
  try:
   x=json.loads(text)
   if isinstance(x,list):return x
  except Exception:pass
 return [x.strip() for x in text.split("|") if x.strip()]

def pathway_rows(candidate):
 raw=_parsed(candidate.get("career__pathways_json"))
 rows=[];seen=set()
 for item in raw:
  if isinstance(item,dict):
   code=clean(item.get("soc_code"));title=clean(item.get("occupation_title")) or None
  else:
   code=clean(item);title=None
  if code and code not in seen:
   seen.add(code);rows.append({"soc_code":code,"occupation_title":title})
 for code in [x.strip() for x in clean(candidate.get("career__soc_codes")).split("|") if x.strip()]:
  if code not in seen:
   seen.add(code);rows.append({"soc_code":code,"occupation_title":None})
 return rows

def representative_rows(candidate):
 raw=_parsed(candidate.get("career__representative_pathways_json") or candidate.get("representative_pathways"))
 out=[]
 for item in raw:
  if isinstance(item,dict):
   code=clean(item.get("soc_code"));title=clean(item.get("occupation_title")) or None
   if code:out.append({"soc_code":code,"occupation_title":title})
 return out

def career_summary(candidate):
 paths=pathway_rows(candidate);reported=candidate.get("career__soc_count")
 try:reported_count=int(float(reported)) if reported not in (None,"") else 0
 except (TypeError,ValueError):reported_count=0
 count=len(paths) if paths else max(reported_count,0)
 return {"pathway_count":count,"soc_codes":[x["soc_code"] for x in paths],"pathways":paths,"representative_pathways":representative_rows(candidate)}
