#!/usr/bin/env python3
"""HTTP smoke test for the fictional College + Career staging service."""
from __future__ import annotations
import argparse,json,subprocess,sys,tempfile,time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from synthetic_staging_bundle import build

PROJECT=Path(__file__).resolve().parent

def request(base,path,method="GET",body=None,origin=None):
 data=None if body is None else json.dumps(body).encode("utf-8")
 headers={"Accept":"application/json"}
 if data is not None:headers["Content-Type"]="application/json"
 if origin:headers["Origin"]=origin
 req=Request(base+path,data=data,headers=headers,method=method)
 with urlopen(req,timeout=5) as r:
  return r.status,dict(r.headers),json.loads(r.read().decode("utf-8"))

def wait(base,deadline=10):
 end=time.time()+deadline
 while time.time()<end:
  try:
   status,_,body=request(base,"/health")
   if status==200 and body.get("status")=="ok":return body
  except Exception:time.sleep(.1)
 raise RuntimeError("staging service did not become healthy")

def run(port=18765):
 with tempfile.TemporaryDirectory() as d:
  root=Path(d);snapshot,manifest=build(root)
  labor=root/"current_labor.json";labor.write_text(json.dumps([
   {"UNITID":"SYN001","program_id":"P1","soc_code":"15-2051","market_id":"35620","market_type":"OEWS_MSA","market_label":"Harbor–Metro Labor Market (fictional)","employment":"1200","employment_state":"observed","median_wage":"94500","wage_state":"observed","source_vintage":"SYNTHETIC"},
   {"UNITID":"SYN002","program_id":"P2","soc_code":"15-1212","market_id":"35620","market_type":"OEWS_MSA","market_label":"Harbor–Metro Labor Market (fictional)","employment":"900","employment_state":"observed","median_wage":"101000","wage_state":"observed","source_vintage":"SYNTHETIC"}
  ]),encoding="utf-8")
  cmd=[sys.executable,str(PROJECT/"service_host.py"),"--snapshot",str(snapshot),"--manifest",str(manifest),"--model-version","synthetic-http-model-1","--current-labor",str(labor),"--allowed-origins","https://staging.example.test","--bind","127.0.0.1","--port",str(port),"--quiet"]
  proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  base=f"http://127.0.0.1:{port}"
  try:
   health=wait(base)
   assert health["production_authorized"] is False and health["candidate_count"]==4
   status,_,metadata=request(base,"/metadata");assert status==200 and metadata["production_authorized"] is False and metadata["data_version"]=="synthetic-http-staging-1"
   status,_,options=request(base,"/options");assert status==200 and options["options"]["counts"]["institution_programs"]==4;assert options["options"]["labor_markets"][0]["value"]=="OEWS_MSA:35620"
   match_body={"schema_version":"1.0","decision_mode":"broad_exploration","constraints":[],"preferences":[],"career_preferences":[],"page":1,"page_size":20}
   status,_,matched=request(base,"/match","POST",match_body);assert status==200 and matched["result_count"]==4 and matched["ordering"]["production_authorized"] is False
   career_body={"schema_version":"1.0","decision_mode":"career_first","constraints":[],"preferences":[{"preference_id":"current_labor_market_priority","dimension":"current_labor_market","importance":1,"priority_explicit":True}],"career_preferences":[],"geography":{"work_market_semantics":"selected_market","intended_work_market":{"market_id":"35620","market_type":"OEWS_MSA"}},"page":1,"page_size":20}
   status,_,career=request(base,"/match","POST",career_body);assert status==200 and career["results"][0]["labor_market"]["selected_work_market"]["market_id"]=="35620"
   try:
    bad=json.loads(json.dumps(career_body));bad["geography"]["intended_work_market"]["market_id"]="99999";request(base,"/match","POST",bad);raise AssertionError("unavailable labor market unexpectedly succeeded")
   except HTTPError as e:
    assert e.code==400
   status,_,candidate=request(base,"/candidate/SYN001%3AP1");assert status==200 and candidate["candidate_id"]=="SYN001:P1";assert {"affordability","aid_context","program_outcomes","transfer","career","labor_market","freshness","unknowns"}.issubset(candidate);assert isinstance(candidate["freshness"]["source_freshness"],list)
   status,_,comparison=request(base,"/compare","POST",{"candidate_ids":["SYN001:P1","SYN002:P2"]});assert status==200 and comparison["candidate_ids"]==["SYN001:P1","SYN002:P2"];assert comparison["semantic_rules"]["no_automatic_winner"] is True and comparison["semantic_rules"]["missing_is_not_zero"] is True;assert comparison["semantic_rules"]["aid_reporting_is_not_individual_award"] is True;assert {"affordability","aid_context","program_outcomes","transfer","career","current_labor","long_term_outlook","accreditation","freshness","unknowns"}.issubset({x["id"] for x in comparison["comparison_dimensions"]})
   status,headers,_=request(base,"/metadata",origin="https://staging.example.test");assert headers.get("Access-Control-Allow-Origin")=="https://staging.example.test"
   status,headers,_=request(base,"/metadata",origin="https://not-allowed.example");assert "Access-Control-Allow-Origin" not in headers
   try:
    request(base,"/compare","POST",{"candidate_ids":["SYN001:P1"]})
    raise AssertionError("invalid compare unexpectedly succeeded")
   except HTTPError as e:
    assert e.code==400
   oversized=Request(base+"/match",data=b"x"*262145,headers={"Content-Type":"application/json","Content-Length":"262145"},method="POST")
   try:
    urlopen(oversized,timeout=5);raise AssertionError("oversized request unexpectedly succeeded")
   except HTTPError as e:
    assert e.code==413
   return {"status":"PASS","base_url":base,"checks":["health","metadata","options","match","career_market_match","invalid_market","candidate","compare","cors_allowed","cors_denied","invalid_compare","payload_limit"]}
  finally:
   proc.terminate()
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.kill()

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--port",type=int,default=18765);a=ap.parse_args();print(json.dumps(run(a.port),indent=2))
if __name__=="__main__":main()
