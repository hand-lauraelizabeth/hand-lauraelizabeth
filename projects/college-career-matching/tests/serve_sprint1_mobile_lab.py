"""Gzipped local fixture for repeatable mobile Lighthouse lab runs.

This serves the SAME published Sprint 1 HTML and JSON payload locally, with
Content-Encoding:gzip for the JSON. It is NOT the WordPress/Divi staging host.
"""
from __future__ import annotations
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import os

ROOT = Path(__file__).resolve().parents[1]
GZIP = ROOT / "data/sprint1/college-search-national.v1.json.gz"
JSON_PATH = "/data/sprint1/college-search-national.v1.json"


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path == JSON_PATH:
            data = GZIP.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        super().end_headers()


if __name__ == "__main__":
    os.chdir(ROOT)
    print("Local compressed College Search lab fixture: http://127.0.0.1:8775/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8775), Handler).serve_forever()
