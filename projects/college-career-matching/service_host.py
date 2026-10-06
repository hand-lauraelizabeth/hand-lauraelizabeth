#!/usr/bin/env python3
"""Zero-dependency HTTP host for the governed College + Career matching service.

The host is safe by default: without an exact production activation record it
serves governed non-production responses. Production authorization is propagated
only when metadata_service_adapter validates the supplied activation record
against the exact snapshot and model identity.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote,urlparse
from candidate_detail_service import candidate_detail
from compare_service_adapter import compare as compare_candidates
from match_service_adapter import match as match_candidates
from metadata_service_adapter import build_metadata
from options_service_adapter import options as build_options

MAX_BODY_BYTES=262144

def clean(v): return str(v).strip() if v is not None else ""
def load_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def read_csv(path):
 with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def truth(v): return clean(v).lower() in {"1","true","yes","y"}

class ServiceState:
 def __init__(self,snapshot_path,manifest_path,model_version,activation_record_path=None,current_labor_path=None,projections_path=None,allowed_origins=None):
  self.snapshot_path=Path(snapshot_path);self.manifest=load_json(manifest_path);self.snapshot=read_csv(snapshot_path);self.model_version=clean(model_version)
  if not self.snapshot:raise ValueError("snapshot is empty")
  actual=sha256(snapshot_path);expected=clean(self.manifest.get("output_sha256")).lower()
  if actual.lower()!=expected:raise ValueError("snapshot SHA-256 does not match manifest output_sha256")
  if self.manifest.get("candidate_count")!=len(self.snapshot):raise ValueError("manifest candidate_count mismatch")
  ids=[clean(r.get("candidate_id")) for r in self.snapshot]
  if any(not x for x in ids) or len(ids)!=len(set(ids)):raise ValueError("snapshot candidate_id values must be unique and nonblank")
  self.by_id={clean(r["candidate_id"]):r for r in self.snapshot}
  self.activation_record=load_json(activation_record_path) if activation_record_path else None
  self.current_labor=load_json(current_labor_path) if current_labor_path else []
  self.projections=load_json(projections_path) if projections_path else []
  self.metadata_response=build_metadata(self.manifest,self.model_version,activation_record=self.activation_record)
  self.production_authorized=self.metadata_response["production_authorized"] is True
  self.data_version=self.metadata_response["data_version"]
  self.allowed_origins={x.strip() for x in (allowed_origins or []) if x.strip()}
  if self.production_authorized and "*" in self.allowed_origins:raise ValueError("production service cannot use wildcard CORS origin")
 def metadata(self):return self.metadata_response
 def options(self):return build_options(self.snapshot,self.data_version,self.current_labor)
 def candidate(self,candidate_id,work_market=None):
  c=self.by_id.get(candidate_id)
  if c is None:raise KeyError(candidate_id)
  return candidate_detail(c,self.current_labor,self.projections,work_market,self.data_version)
 def match(self,request):
  return match_candidates(request,self.snapshot,self.data_version,self.model_version,self.current_labor,self.projections,production_authorized=self.production_authorized)
 def compare(self,request):
  ids=request.get("candidate_ids")
  if not isinstance(ids,list):raise ValueError("candidate_ids must be an array")
  missing=[x for x in ids if x not in self.by_id]
  if missing:raise KeyError(",".join(missing))
  work_market=request.get("intended_work_market")
  return compare_candidates([self.by_id[x] for x in ids],self.current_labor,self.projections,work_market,self.data_version)
 def health(self):
  return {"schema_version":"1.0","status":"ok","data_version":self.data_version,"model_version":self.model_version,"production_authorized":self.production_authorized,"candidate_count":len(self.snapshot)}

class Handler(BaseHTTPRequestHandler):
 server_version="CollegeCareerService/1.0"
 def _origin(self):
  origin=clean(self.headers.get("Origin"))
  if not origin:return None
  allowed=self.server.state.allowed_origins
  if "*" in allowed:return "*"
  return origin if origin in allowed else None
 def _headers(self,status=200,content_type="application/json; charset=utf-8"):
  self.send_response(status);self.send_header("Content-Type",content_type);self.send_header("Cache-Control","no-store")
  origin=self._origin()
  if origin:self.send_header("Access-Control-Allow-Origin",origin);self.send_header("Vary","Origin")
  self.end_headers()
 def _json(self,obj,status=200):
  data=json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode("utf-8");self._headers(status);self.wfile.write(data)
 def _error(self,status,code,message):
  self._json({"schema_version":"1.0","error":{"code":code,"message":message}},status)
 def _read_json(self):
  try:length=int(self.headers.get("Content-Length","0"))
  except ValueError:raise ValueError("invalid Content-Length")
  if length<1:raise ValueError("request body is required")
  if length>MAX_BODY_BYTES:raise OverflowError("request body exceeds 256 KiB")
  raw=self.rfile.read(length)
  try:return json.loads(raw.decode("utf-8"))
  except Exception as e:raise ValueError("request body must be valid UTF-8 JSON") from e
 def do_OPTIONS(self):
  if not self._origin():return self._error(403,"origin_not_allowed","Origin is not allowed")
  self.send_response(204);self.send_header("Access-Control-Allow-Origin",self._origin());self.send_header("Vary","Origin");self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS");self.send_header("Access-Control-Allow-Headers","Content-Type");self.end_headers()
 def do_GET(self):
  path=urlparse(self.path).path
  try:
   if path=="/health":return self._json(self.server.state.health())
   if path=="/metadata":return self._json(self.server.state.metadata())
   if path=="/options":return self._json(self.server.state.options())
   if path.startswith("/candidate/"):return self._json(self.server.state.candidate(unquote(path[len("/candidate/"):])))
   return self._error(404,"not_found","Endpoint not found")
  except KeyError:return self._error(404,"candidate_not_found","Candidate not found")
  except Exception as e:return self._error(400,"request_error",str(e))
 def do_POST(self):
  path=urlparse(self.path).path
  try:
   body=self._read_json()
   if path=="/match":return self._json(self.server.state.match(body))
   if path=="/compare":return self._json(self.server.state.compare(body))
   return self._error(404,"not_found","Endpoint not found")
  except OverflowError as e:return self._error(413,"payload_too_large",str(e))
  except KeyError as e:return self._error(404,"candidate_not_found",str(e).strip("'"))
  except ValueError as e:return self._error(400,"invalid_request",str(e))
  except Exception:return self._error(500,"internal_error","Unexpected service error")
 def log_message(self,fmt,*args):
  if getattr(self.server,"quiet",False):return
  super().log_message(fmt,*args)

def parse_origins(value):
 return [x.strip() for x in clean(value).split(",") if x.strip()]

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--snapshot",default=os.environ.get("CCX_SNAPSHOT"))
 ap.add_argument("--manifest",default=os.environ.get("CCX_MANIFEST"))
 ap.add_argument("--model-version",default=os.environ.get("CCX_MODEL_VERSION"))
 ap.add_argument("--activation-record",default=os.environ.get("CCX_ACTIVATION_RECORD"))
 ap.add_argument("--current-labor",default=os.environ.get("CCX_CURRENT_LABOR"))
 ap.add_argument("--projections",default=os.environ.get("CCX_PROJECTIONS"))
 ap.add_argument("--allowed-origins",default=os.environ.get("CCX_ALLOWED_ORIGINS",""))
 ap.add_argument("--bind",default=os.environ.get("CCX_BIND","0.0.0.0"));ap.add_argument("--port",type=int,default=int(os.environ.get("PORT","8080")));ap.add_argument("--quiet",action="store_true")
 a=ap.parse_args()
 for name,value in [("snapshot",a.snapshot),("manifest",a.manifest),("model-version",a.model_version)]:
  if not value:ap.error(f"--{name} or its environment variable is required")
 state=ServiceState(a.snapshot,a.manifest,a.model_version,a.activation_record,a.current_labor,a.projections,parse_origins(a.allowed_origins))
 httpd=ThreadingHTTPServer((a.bind,a.port),Handler);httpd.state=state;httpd.quiet=a.quiet
 print(f"College + Career service listening on http://{a.bind}:{a.port} · data={state.data_version} · model={state.model_version} · production_authorized={str(state.production_authorized).lower()}")
 httpd.serve_forever()
if __name__=="__main__":main()
