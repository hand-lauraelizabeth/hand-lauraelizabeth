#!/usr/bin/env python3
"""Zero-dependency local prototype server using synthetic fixtures only."""
from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  p="index.html" if self.path in {"/","/index.html"} else self.path.lstrip("/")
  f=(ROOT/p).resolve()
  if ROOT not in f.parents and f!=ROOT:return self.send_error(403)
  if not f.exists():return self.send_error(404)
  data=f.read_bytes();self.send_response(200);self.send_header("Content-Type",{".html":"text/html; charset=utf-8",".js":"text/javascript; charset=utf-8",".css":"text/css; charset=utf-8",".json":"application/json"}.get(f.suffix,"application/octet-stream"));self.end_headers();self.wfile.write(data)
if __name__=="__main__":
 print("Synthetic College + Career prototype: http://127.0.0.1:8000")
 ThreadingHTTPServer(("127.0.0.1",8000),H).serve_forever()
