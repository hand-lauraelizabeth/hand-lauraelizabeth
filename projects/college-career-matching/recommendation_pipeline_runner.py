#!/usr/bin/env python3
"""Run configured recommendation stages in dependency order with provenance.

Commands are parsed into argv and executed without a shell so future service/session
input cannot become shell syntax. Paths are resolved deterministically relative to
the stage manifest unless explicitly absolute or rooted in {run_dir}/{project_dir}.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, shlex, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR=Path(__file__).resolve().parent

def sha256(p: Path):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
 return h.hexdigest()

def split(v): return [x.strip() for x in str(v).split(";") if x.strip()]
def truth(v): return str(v).strip().lower() in {"1","true","yes","y"}
def expand(v,python,run_dir,manifest_dir):
 return str(v).replace("{python}",str(python)).replace("{run_dir}",str(run_dir)).replace("{manifest_dir}",str(manifest_dir)).replace("{project_dir}",str(PROJECT_DIR))
def resolve_path(v,python,run_dir,manifest_dir):
 p=Path(expand(v,python,run_dir,manifest_dir)).expanduser()
 return p if p.is_absolute() else manifest_dir/p
def file_hashes_from_argv(argv,manifest_dir):
 out={}
 for token in argv:
  p=Path(token)
  if not p.is_absolute(): p=manifest_dir/p
  if p.is_file(): out[str(p.resolve())]=sha256(p)
 return out

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--stage-manifest",type=Path,required=True); ap.add_argument("--run-dir",type=Path,required=True); ap.add_argument("--python",default=sys.executable); a=ap.parse_args()
 a.stage_manifest=a.stage_manifest.resolve(); a.run_dir=a.run_dir.resolve(); manifest_dir=a.stage_manifest.parent
 a.run_dir.mkdir(parents=True,exist_ok=True); run_started=datetime.now(timezone.utc).isoformat()
 with a.stage_manifest.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
 required={"stage_id","command","depends_on","required","inputs","outputs"}
 if not rows or not required.issubset(rows[0]): raise ValueError(f"stage manifest requires {sorted(required)}")
 ids=[r["stage_id"].strip() for r in rows]
 if not all(ids): raise ValueError("stage_id cannot be blank")
 if len(ids)!=len(set(ids)): raise ValueError("duplicate stage_id")
 known=set(ids)
 for r in rows:
  r["stage_id"]=r["stage_id"].strip(); unknown=set(split(r["depends_on"]))-known
  if unknown: raise ValueError(f"{r['stage_id']} has unknown dependencies {sorted(unknown)}")
 status={}; records=[]; pending={r["stage_id"]:r for r in rows}
 while pending:
  progressed=False
  for sid,r in list(pending.items()):
   deps=split(r["depends_on"])
   if any(d in pending for d in deps): continue
   progressed=True; required_stage=truth(r["required"])
   # A declared dependency must pass. Optionality controls release blocking, not dependency truth.
   blocked_deps=[d for d in deps if status.get(d)!="PASS"]
   if blocked_deps:
    rec={"stage_id":sid,"status":"BLOCKED_BY_DEPENDENCY","required":required_stage,"dependencies":deps,"blocked_dependencies":blocked_deps}
   else:
    ins=[resolve_path(x,a.python,a.run_dir,manifest_dir) for x in split(r["inputs"])]
    missing=[str(x) for x in ins if not x.exists()]
    if missing:
     rec={"stage_id":sid,"status":"FAIL" if required_stage else "OPTIONAL_FAIL","required":required_stage,"dependencies":deps,"missing_inputs":missing}
    else:
     before={str(x):sha256(x) for x in ins}
     command_text=expand(r["command"],a.python,a.run_dir,manifest_dir)
     argv=shlex.split(command_text,posix=True)
     if not argv: raise ValueError(f"{sid} has blank command")
     command_file_sha256=file_hashes_from_argv(argv,manifest_dir)
     started=time.time(); proc=subprocess.run(argv,shell=False,text=True,capture_output=True,cwd=manifest_dir); elapsed=time.time()-started
     outs=[resolve_path(x,a.python,a.run_dir,manifest_dir) for x in split(r["outputs"])]
     missing_out=[str(x) for x in outs if not x.exists()]
     ok=proc.returncode==0 and not missing_out
     rec={"stage_id":sid,"status":"PASS" if ok else ("FAIL" if required_stage else "OPTIONAL_FAIL"),"required":required_stage,"dependencies":deps,"argv":argv,"return_code":proc.returncode,"elapsed_seconds":round(elapsed,6),"input_sha256":before,"command_file_sha256":command_file_sha256,"output_sha256":{str(x):sha256(x) for x in outs if x.exists()},"missing_outputs":missing_out,"stdout_tail":proc.stdout[-4000:],"stderr_tail":proc.stderr[-4000:]}
   status[sid]=rec["status"]; records.append(rec); del pending[sid]
  if not progressed: raise ValueError("cyclic stage dependencies")
 overall="BLOCKED" if any(r["required"] and r["status"]!="PASS" for r in records) else "PIPELINE_COMPLETED"
 manifest={"run_started_utc":run_started,"run_finished_utc":datetime.now(timezone.utc).isoformat(),"stage_manifest":str(a.stage_manifest),"stage_manifest_sha256":sha256(a.stage_manifest),"manifest_directory":str(manifest_dir),"project_directory":str(PROJECT_DIR),"overall_status":overall,"stages":records,"rule":"PIPELINE_COMPLETED means configured stages executed successfully; it is not recommendation release authorization. Run the separate release gate."}
 (a.run_dir/"recommendation_pipeline_run_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
 if overall=="BLOCKED": sys.exit(2)

if __name__=="__main__": main()
