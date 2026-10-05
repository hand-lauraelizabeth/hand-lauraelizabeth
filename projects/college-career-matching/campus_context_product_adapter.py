#!/usr/bin/env python3
"""Normalize campus-context evidence at UNITID grain with field-level provenance.

This module expects source-specific ingestion to have already mapped raw IPEDS,
BTS, EPA, or other governed fields into the canonical names below. It preserves
unknown states and never turns missing accessibility or affordability evidence
into a negative fact.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

EVIDENCE_STATES={"observed","missing","suppressed","unresolved","not_published"}
LOCALE_GROUPS={
 "11":"City","12":"City","13":"City",
 "21":"Suburban","22":"Suburban","23":"Suburban",
 "31":"Town","32":"Town","33":"Town",
 "41":"Rural","42":"Rural","43":"Rural",
}
BOOLEAN_FIELDS={"housing_available","housing_required_all_ftft"}
CANONICAL_FIELDS=(
 "locale_code",
 "housing_available",
 "housing_capacity",
 "housing_required_all_ftft",
 "net_price_income_0_30k",
 "net_price_income_30_48k",
 "net_price_income_48_75k",
 "net_price_income_75_110k",
 "net_price_income_110k_plus",
 "institutional_grant_share",
 "work_study_share",
 "state_local_grant_share",
 "disability_services_registered_share",
 "transit_stop_distance_m",
 "transit_stop_count_800m",
 "walkability_index",
)
INCOME_BAND_FIELDS={
 "0_30k":"net_price_income_0_30k",
 "30_48k":"net_price_income_30_48k",
 "48_75k":"net_price_income_48_75k",
 "75_110k":"net_price_income_75_110k",
 "110k_plus":"net_price_income_110k_plus",
}

def clean(value):
 return str(value).strip() if value is not None else ""

def read(path):
 with Path(path).open(newline="",encoding="utf-8-sig") as handle:
  return list(csv.DictReader(handle))

def canonical_bool(value,field):
 raw=clean(value).lower()
 if raw=="":return ""
 if raw in {"1","true","yes","y"}:return "true"
 if raw in {"0","false","no","n"}:return "false"
 raise ValueError(f"{field}: expected normalized boolean, got {value!r}")

def field_state(row,field):
 raw=clean(row.get(f"{field}__state")).lower()
 if raw:
  if raw not in EVIDENCE_STATES:raise ValueError(f"{field}: invalid evidence state {raw}")
  return raw
 return "missing" if clean(row.get(field))=="" else "observed"

def normalize(rows):
 if not rows:return []
 seen=set();out=[]
 for i,row in enumerate(rows,1):
  uid=clean(row.get("UNITID"))
  if not uid:raise ValueError(f"row {i}: blank UNITID")
  if uid in seen:raise ValueError(f"duplicate UNITID: {uid}")
  seen.add(uid);record={"UNITID":uid}
  for field in CANONICAL_FIELDS:
   value=canonical_bool(row.get(field),field) if field in BOOLEAN_FIELDS else clean(row.get(field))
   state=field_state(row,field)
   record[field]=value
   record[f"{field}__state"]=state
   record[f"{field}__source_id"]=clean(row.get(f"{field}__source_id"))
   record[f"{field}__source_vintage"]=clean(row.get(f"{field}__source_vintage"))
  locale=record["locale_code"]
  if locale and locale not in LOCALE_GROUPS:raise ValueError(f"locale_code: unsupported NCES locale {locale}")
  record["setting_group"]=LOCALE_GROUPS.get(locale,"")
  record["setting_group__state"]=record["locale_code__state"] if locale else "missing"
  record["setting_group__source_id"]=record["locale_code__source_id"]
  record["setting_group__source_vintage"]=record["locale_code__source_vintage"]
  housing=record["housing_available"];required=record["housing_required_all_ftft"]
  if housing=="false":choice="no_institutional_housing"
  elif housing=="true" and required=="false":choice="choice_available"
  elif housing=="true" and required=="true":choice="required_for_all_ftft"
  else:choice="unknown"
  record["housing_choice_state"]=choice
  for field,prefix in [
   ("institutional_grant_share","institutional_grant"),
   ("work_study_share","work_study"),
   ("state_local_grant_share","state_local_grant"),
   ("disability_services_registered_share","disability_services"),
  ]:
   record[f"{prefix}_evidence_available"]="true" if record[f"{field}__state"]=="observed" else "false"
  out.append(record)
 return out

def income_band_field(band):
 if band not in INCOME_BAND_FIELDS:raise ValueError(f"unsupported income band: {band}")
 return INCOME_BAND_FIELDS[band]

def write_csv(path,rows):
 if not rows:return
 columns=[]
 for row in rows:
  for key in row:
   if key not in columns:columns.append(key)
 with path.open("w",newline="",encoding="utf-8") as handle:
  writer=csv.DictWriter(handle,fieldnames=columns);writer.writeheader();writer.writerows(rows)

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--input",type=Path,required=True)
 parser.add_argument("--out-dir",type=Path,required=True)
 args=parser.parse_args()
 rows=normalize(read(args.input));args.out_dir.mkdir(parents=True,exist_ok=True)
 write_csv(args.out_dir/"campus_context.csv",rows)
 qa={
  "records":len(rows),
  "setting_groups":{group:sum(r["setting_group"]==group for r in rows) for group in sorted(set(LOCALE_GROUPS.values()))},
  "observed_fields":{field:sum(r[f"{field}__state"]=="observed" for r in rows) for field in CANONICAL_FIELDS},
  "rules":[
   "Missing evidence is not zero or false.",
   "NCES locale detail is retained while a four-category setting is derived.",
   "Housing availability and universal FTFT residency requirements remain distinct.",
   "Income-band net prices remain separate published averages, not personalized estimates.",
   "Transit, walkability, and disability-services evidence remain separate accessibility signals.",
   "Every canonical field can retain source_id and source_vintage independently."
  ]
 }
 (args.out_dir/"campus_context_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")

if __name__=="__main__":main()
