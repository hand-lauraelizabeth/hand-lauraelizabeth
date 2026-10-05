#!/usr/bin/env python3
"""Fail-closed QA gate for activating an institution×program product snapshot.

Thresholds are supplied in policy JSON; this module invents none. It validates
identity, counts, coverage, provenance, freshness metadata, and UI-option buildability.
"""
from __future__ import annotations
import argparse,csv,json
from datetime import datetime,timezone
from pathlib import Path
from interface_options_builder import build as build_options

def load_json(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def load_csv(p):
 with Path(p).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def n(v):
 try:return float(v)
 except (TypeError,ValueError):return None
def check(cid,passed,actual,expected,required=True,message=""):
 return {"check_id":cid,"required":required,"status":"PASS" if passed else ("FAIL" if required else "WARN"),"actual":actual,"expected":expected,"message":message}
def evaluate(snapshot,manifest,policy):
 out=[];required_fields=policy.get("required_fields",["candidate_id","UNITID","institution_name","program_id","program_name","cip_code","credential_level","state"])
 missing=[f for f in required_fields if not snapshot or f not in snapshot[0]];out.append(check("required_fields",not missing,missing,"none missing",True))
 if snapshot:
  blanks={f:sum(not str(r.get(f,"")).strip() for r in snapshot) for f in required_fields if f in snapshot[0]};bad={k:v for k,v in blanks.items() if v};out.append(check("required_fields_nonblank",not bad,bad,"0 blanks",True))
  keys=[(str(r.get("UNITID","")).strip(),str(r.get("program_id","")).strip()) for r in snapshot];out.append(check("candidate_identity_unique",len(keys)==len(set(keys)),len(keys)-len(set(keys)),"0 duplicates",True))
 count=len(snapshot);floor=policy.get("min_candidate_count");out.append(check("candidate_count_floor",floor is None or count>=floor,count,f">={floor}" if floor is not None else "not configured",floor is not None))
 inst=len({str(r.get("UNITID","")).strip() for r in snapshot if str(r.get("UNITID","")).strip()});floor=policy.get("min_institution_count");out.append(check("institution_count_floor",floor is None or inst>=floor,inst,f">={floor}" if floor is not None else "not configured",floor is not None))
 prev=policy.get("previous_candidate_count");ratio=policy.get("min_candidate_retention_ratio")
 if prev is not None and ratio is not None:out.append(check("candidate_retention",count>=float(prev)*float(ratio),count/float(prev) if float(prev) else None,f">={ratio}",True))
 for family,min_rate in policy.get("min_coverage_rate",{}).items():
  col=f"coverage__{family}";present=sum(str(r.get(col,"0")).strip().lower() in {"1","true","yes"} for r in snapshot);rate=present/count if count else 0;out.append(check(f"coverage_{family}",rate>=float(min_rate),rate,f">={min_rate}",True))
 hashes=manifest.get("input_sha256",{});out.append(check("input_hashes_present",bool(hashes) and all(len(str(v))==64 for v in hashes.values()),len(hashes),">=1 valid SHA-256",True))
 out.append(check("manifest_candidate_count",manifest.get("candidate_count")==count,manifest.get("candidate_count"),count,True))
 out.append(check("manifest_data_version",bool(str(manifest.get("data_version","")).strip()),manifest.get("data_version"),"nonblank",True))
 required_vintages=policy.get("required_source_vintages",[]);vintages=manifest.get("source_vintages",{})
 for source in required_vintages:out.append(check(f"vintage_{source}",bool(str(vintages.get(source,"")).strip()),vintages.get(source),"nonblank",True))
 try:
  opts=build_options(snapshot,str(manifest.get("data_version","")));ok=opts["counts"]["institution_programs"]==count;actual=opts["counts"]["institution_programs"]
 except Exception as e:ok=False;actual=f"ERROR: {e}"
 out.append(check("interface_options_build",ok,actual,count,True))
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--snapshot",type=Path,required=True);ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--policy",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args();checks=evaluate(load_csv(a.snapshot),load_json(a.manifest),load_json(a.policy));blocked=any(x["status"]=="FAIL" for x in checks);decision={"schema_version":"1.0","evaluated_at_utc":datetime.now(timezone.utc).isoformat(),"decision":"BLOCKED" if blocked else "ELIGIBLE_FOR_ACTIVATION_REVIEW","checks":checks};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(decision,indent=2),encoding="utf-8");raise SystemExit(2 if blocked else 0)
if __name__=="__main__":main()
