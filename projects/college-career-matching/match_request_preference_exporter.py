#!/usr/bin/env python3
"""Export validated match-request preferences for recommendation composition.

This is a shape bridge only. It does not add defaults, alter importance values,
or convert hard constraints into preferences.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from match_service_adapter import validate_request

DIM_COLUMNS=("preference_id","dimension","importance","priority_explicit","source_question_id")
CAREER_COLUMNS=("preference_id","attribute_id","operator","importance","priority_explicit","target_value","target_min","target_max","scale_min","scale_max","source_question_id")

def clean(v):return str(v).strip() if v is not None else ""

def export_preferences(request):
 validate_request(request)
 dims=[]
 for p in request.get("preferences",[]):
  dims.append({
   "preference_id":clean(p.get("preference_id")),
   "dimension":clean(p.get("dimension")),
   "importance":p.get("importance"),
   "priority_explicit":"true",
   "source_question_id":clean(p.get("source_question_id")),
  })
 careers=[]
 for p in request.get("career_preferences",[]):
  careers.append({k:("true" if k=="priority_explicit" else p.get(k,"")) for k in CAREER_COLUMNS})
 qa={
  "schema_version":"1.0",
  "dimension_preference_count":len(dims),
  "career_preference_count":len(careers),
  "rules":[
   "The request is validated before export.",
   "Only request-supplied explicit priorities are exported.",
   "Importance values are preserved exactly and are not normalized in this bridge.",
   "Hard constraints remain separate and are not converted into preference weights."
  ]
 }
 return dims,careers,qa

def write_csv(path,rows,columns):
 with Path(path).open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--request",type=Path,required=True);ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 request=json.loads(a.request.read_text(encoding="utf-8"));dims,careers,qa=export_preferences(request)
 write_csv(a.out_dir/"explicit_dimension_preferences.csv",dims,DIM_COLUMNS)
 write_csv(a.out_dir/"explicit_career_preferences.csv",careers,CAREER_COLUMNS)
 (a.out_dir/"request_preference_export_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")

if __name__=="__main__":main()
