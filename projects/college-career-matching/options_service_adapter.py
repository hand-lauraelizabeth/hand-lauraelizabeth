#!/usr/bin/env python3
"""Service wrapper for current-data interface options and constraint capabilities."""
from __future__ import annotations
from interface_options_builder import build as build_options
from constraint_field_registry import public_registry
from onet_career_attribute_registry import public_options as career_attribute_options

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

def options(snapshot,data_version,current_labor=None,career_attributes=None):
 o=build_options(snapshot,data_version)
 o["labor_markets"]=labor_market_options(current_labor)
 active={clean(x.get("attribute_id")) for x in career_attributes or [] if clean(x.get("attribute_id"))}
 o["career_preference_attributes"]=[x for x in career_attribute_options() if x["attribute_id"] in active]
 return {"schema_version":"1.0","data_version":data_version,"options":o,"constraint_capabilities":public_registry(),"semantic_rules":{"options_source":"active product snapshot plus loaded governed labor/career evidence","unknown_evidence":"unknown is not false or zero","career_preference_options":"advertise only reviewed O*NET attributes present in the active career evidence","browser_role":"render choices; do not invent constraint fields, operators, labor-market geography, or career-attribute mappings"}}
