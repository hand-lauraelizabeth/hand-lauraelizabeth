#!/usr/bin/env python3
"""Governed O*NET career-preference attribute registry."""
from __future__ import annotations
import json
from pathlib import Path
REGISTRY_PATH=Path(__file__).resolve().parent/"config/onet_career_attribute_registry.v1.json"

def load_registry(path=REGISTRY_PATH):
 data=json.loads(Path(path).read_text(encoding="utf-8"))
 if data.get("schema_version")!="1.0":raise ValueError("unsupported O*NET career registry schema")
 attrs=data.get("attributes") or [];seen_q=set();seen_a=set();seen_e=set()
 source=data.get("source") or {}
 if source.get("release")!="31.0" or source.get("domain")!="work_activities" or source.get("scale_id")!="IM":raise ValueError("unexpected O*NET career registry source contract")
 if source.get("scale_min")!=1 or source.get("scale_max")!=5:raise ValueError("O*NET Importance scale must be 1..5")
 for a in attrs:
  for k in ["question_id","attribute_id","element_id","element_name","prompt","operator","scale_id","scale_min","scale_max","review_status"]:
   if k not in a:raise ValueError(f"career registry attribute missing {k}")
  if a["question_id"] in seen_q or a["attribute_id"] in seen_a or a["element_id"] in seen_e:raise ValueError("duplicate governed career attribute identity")
  seen_q.add(a["question_id"]);seen_a.add(a["attribute_id"]);seen_e.add(a["element_id"])
  if a["review_status"]!="approved" or a["operator"]!="higher_preferred" or a["scale_id"]!="IM" or a["scale_min"]!=1 or a["scale_max"]!=5:raise ValueError(f"{a['question_id']}: unsupported reviewed mapping")
 return data

def by_question(path=REGISTRY_PATH):return {x["question_id"]:x for x in load_registry(path)["attributes"]}
def by_attribute(path=REGISTRY_PATH):return {x["attribute_id"]:x for x in load_registry(path)["attributes"]}
def public_options(path=REGISTRY_PATH):
 return [{"question_id":x["question_id"],"attribute_id":x["attribute_id"],"label":x["element_name"],"prompt":x["prompt"],"operator":x["operator"],"scale_min":x["scale_min"],"scale_max":x["scale_max"],"source_release":"O*NET 31.0","source_domain":"Work Activities","scale_name":"Importance"} for x in load_registry(path)["attributes"]]
