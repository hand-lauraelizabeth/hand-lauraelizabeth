#!/usr/bin/env python3
"""Service wrapper for current-data interface options and constraint capabilities."""
from __future__ import annotations
from interface_options_builder import build as build_options
from constraint_field_registry import public_registry

def clean(v):return str(v).strip() if v is not None else ""

def labor_market_options(rows):
 seen={}
 for r in rows or []:
  market_id=clean(r.get("market_id"));market_type=clean(r.get("market_type"))
  if not market_id or not market_type:continue
  key=(market_type,market_id)
  label=clean(r.get("market_label") or r.get("market_title") or r.get("area_title") or r.get("AREA_TITLE")) or f"{market_type} {market_id}"
  seen.setdefault(key,label)
 return [{"value":f"{market_type}:{market_id}","label":label,"market_id":market_id,"market_type":market_type} for (market_type,market_id),label in sorted(seen.items(),key=lambda x:(x[1].casefold(),x[0][0],x[0][1]))]

def options(snapshot,data_version,current_labor=None):
 o=build_options(snapshot,data_version)
 o["labor_markets"]=labor_market_options(current_labor)
 return {"schema_version":"1.0","data_version":data_version,"options":o,"constraint_capabilities":public_registry(),"semantic_rules":{"options_source":"active product snapshot plus loaded governed labor evidence","unknown_evidence":"unknown is not false or zero","browser_role":"render choices; do not invent constraint fields, operators, or labor-market geography"}}
