#!/usr/bin/env python3
"""Build and serve a loopback-only browser harness for the real explorer UI.

The harness uses fictional staging records and the real HTTP service/client
boundary. It never creates production authorization and never binds off-loopback.
"""
from __future__ import annotations
import argparse,json,subprocess,sys,tempfile,threading,time
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from public_explorer_deployment import inject
from service_runtime_config import build_staging
from synthetic_staging_bundle import build as build_staging_bundle

PROJECT=Path(__file__).resolve().parent

def build_harness(output,api_port=18765,candidate_count=None):
 output=Path(output)
 staging_dir=output.parent/"staging-data"
 snapshot,manifest_path=build_staging_bundle(staging_dir,candidate_count=candidate_count)
 manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
 runtime=build_staging(f"http://127.0.0.1:{api_port}",manifest["data_version"],"synthetic-http-model-1",manifest["output_sha256"])
 source=(PROJECT/"public-explorer.html").read_text(encoding="utf-8")
 html=inject(source,runtime)
 html=html.replace("<head>","<head>\n<meta name=\"robots\" content=\"noindex,nofollow\">",1)
 html=html.replace("<title>College + Career Explorer — Public Interaction Sample</title>","<title>College + Career Explorer — Synthetic Staging Harness</title>")
 output.write_text(html,encoding="utf-8")
 return {"snapshot":snapshot,"manifest":manifest_path,"runtime":runtime,"output":output}

class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def serve(ui_port=18766,api_port=18765):
 if ui_port==api_port:raise ValueError("UI and API ports must differ")
 if not (1<=ui_port<=65535 and 1<=api_port<=65535):raise ValueError("ports must be 1..65535")
 built=build_harness(PROJECT/"staging-browser.html",api_port)
 origin=f"http://127.0.0.1:{ui_port}"
 cmd=[sys.executable,str(PROJECT/"service_host.py"),"--snapshot",str(built["snapshot"]),"--manifest",str(built["manifest"]),"--model-version","synthetic-http-model-1","--allowed-origins",origin,"--bind","127.0.0.1","--port",str(api_port),"--quiet"]
 proc=subprocess.Popen(cmd)
 handler=partial(Quiet,directory=str(PROJECT))
 httpd=ThreadingHTTPServer(("127.0.0.1",ui_port),handler)
 try:
  time.sleep(.25)
  if proc.poll() is not None:raise RuntimeError("staging API failed to start")
  print(f"Synthetic staging explorer: {origin}/staging-browser.html")
  print(f"Synthetic staging API: http://127.0.0.1:{api_port}")
  print("Loopback only · fictional data · production_authorized=false")
  httpd.serve_forever()
 finally:
  httpd.server_close();proc.terminate()
  try:proc.wait(timeout=3)
  except subprocess.TimeoutExpired:proc.kill()

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--ui-port",type=int,default=18766);ap.add_argument("--api-port",type=int,default=18765);ap.add_argument("--build-only",action="store_true");ap.add_argument("--output",type=Path,default=PROJECT/"staging-browser.html");a=ap.parse_args()
 if a.build_only:
  x=build_harness(a.output,a.api_port);print(json.dumps({"output":str(x["output"]),"mode":x["runtime"]["mode"],"production_authorized":x["runtime"]["production_authorized"]},indent=2))
 else:serve(a.ui_port,a.api_port)
if __name__=="__main__":main()
