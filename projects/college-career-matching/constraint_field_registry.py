#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
PATH=Path(__file__).parent/"config"/"constraint_field_registry.v1.json"
def load_registry(path=PATH):
 r=json.loads(Path(path).read_text(encoding="utf-8"))
 if not r.get("fields"):raise ValueError("constraint field registry is empty")
 return r
def validate_constraint(c,registry=None):
 r=registry or load_registry();field=c.get("field")
 if field not in r["fields"]:raise ValueError(f"constraint field not governed: {field}")
 spec=r["fields"][field]
 if spec.get("hard_constraint_allowed") is not True:raise ValueError(f"hard constraint not allowed: {field}")
 if c.get("operator") not in spec.get("operators",[]):raise ValueError(f"operator {c.get('operator')} not allowed for {field}")
 return spec
def public_registry(registry=None):
 r=registry or load_registry();return {"schema_version":r["schema_version"],"fields":r["fields"]}
