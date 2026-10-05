#!/usr/bin/env python3
"""Inject a governed runtime config into the public explorer HTML.

This is a build step, not an activation step. A production runtime config must
already have been produced from a valid activation record.
"""
from __future__ import annotations
import argparse,html,json,re
from pathlib import Path

def inject(source,runtime):
 if runtime.get("schema_version")!="1.0": raise ValueError("unsupported runtime config schema")
 mode=runtime.get("mode")
 if mode not in {"fixture","production"}: raise ValueError("unsupported runtime mode")
 if mode=="production" and runtime.get("production_authorized") is not True: raise ValueError("production runtime is not authorized")
 if mode=="fixture" and runtime.get("production_authorized") is not False: raise ValueError("fixture runtime must not be production authorized")
 payload=json.dumps(runtime,separators=(",",":"),ensure_ascii=False).replace("</","<\/")
 marker='<script type="application/json" id="ccx-runtime-config">'
 block=marker+payload+"</script>"
 if marker in source:
  source=re.sub(r'<script type="application/json" id="ccx-runtime-config">.*?</script>',block,source,flags=re.S)
 else:
  source=source.replace('<div id="leh-ccx">','<div id="leh-ccx">\n  '+block,1)
 return source

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--source",type=Path,required=True);ap.add_argument("--runtime-config",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
 runtime=json.loads(a.runtime_config.read_text(encoding="utf-8"));out=inject(a.source.read_text(encoding="utf-8"),runtime);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(out,encoding="utf-8")
if __name__=="__main__":main()
