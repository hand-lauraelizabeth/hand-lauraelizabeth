#!/usr/bin/env python3
"""Normalize authoritative accreditation evidence to institution grain.

No institution is treated as unaccredited merely because it is absent from the
source extract. Multiple agency records are summarized without inventing a single
quality score.
"""
from __future__ import annotations
import argparse,csv,json
from collections import defaultdict
from pathlib import Path
REQUIRED={"UNITID","agency_name","accreditation_status"}
def read(p):
 with Path(p).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def clean(v):return str(v).strip() if v is not None else ""
def build(rows):
 if not rows:raise ValueError("accreditation extract is empty")
 miss=REQUIRED-set(rows[0]);
 if miss:raise ValueError(f"accreditation extract missing {sorted(miss)}")
 groups=defaultdict(list)
 for r in rows:
  uid=clean(r["UNITID"])
  if not uid:raise ValueError("blank UNITID in accreditation extract")
  groups[uid].append(r)
 out=[]
 for uid,rs in groups.items():
  agencies=sorted({clean(r["agency_name"]) for r in rs if clean(r["agency_name"])})
  statuses=sorted({clean(r["accreditation_status"]) for r in rs if clean(r["accreditation_status"])})
  out.append({"UNITID":uid,"record_count":str(len(rs)),"agency_names":" | ".join(agencies),"statuses":" | ".join(statuses),"evidence_present":"1","source_record_ids":" | ".join(sorted({clean(r.get('source_record_id')) for r in rs if clean(r.get('source_record_id'))}))})
 out.sort(key=lambda r:r["UNITID"]);return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,required=True);ap.add_argument("--source-vintage",required=True);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--qa",type=Path,required=True);a=ap.parse_args();rows=build(read(a.input));a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 a.qa.write_text(json.dumps({"source_vintage":a.source_vintage,"institution_with_accreditation_evidence_count":len(rows),"semantic_rule":"Absence from this enrichment extract is unknown coverage, not an unaccredited determination."},indent=2),encoding="utf-8")
if __name__=="__main__":main()
