#!/usr/bin/env python3
"""Validate governed product enrichment families before snapshot assembly."""
from __future__ import annotations
import json
from pathlib import Path
REGISTRY_PATH=Path(__file__).with_name("governed_product_enrichment_registry.v1.json")
def load_registry(path=REGISTRY_PATH):
 r=json.loads(Path(path).read_text(encoding="utf-8"))
 if not r.get("families"):raise ValueError("enrichment registry has no families")
 return r
def validate_family(name,rows,registry=None):
 registry=registry or load_registry();families=registry["families"]
 if name not in families:raise ValueError(f"unregistered enrichment family: {name}")
 spec=families[name];keys=spec["join_grain"]
 if not rows:return {"family":name,"row_count":0,"join_grain":keys,"status":"EMPTY"}
 missing=[k for k in keys if k not in rows[0]]
 if missing:raise ValueError(f"{name}: missing join columns {missing}")
 seen=set()
 for i,r in enumerate(rows,1):
  key=tuple(str(r.get(k,"")).strip() for k in keys)
  if not all(key):raise ValueError(f"{name}: blank join key at row {i}: {key}")
  if key in seen:raise ValueError(f"{name}: duplicate join key {key}")
  seen.add(key)
 return {"family":name,"row_count":len(rows),"join_grain":keys,"status":"PASS"}
def validate_all(enrichments,registry=None):
 registry=registry or load_registry();return {name:validate_family(name,rows,registry) for name,rows in enrichments.items()}
