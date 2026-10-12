"""Gzip-enabled static fixture for the Sprint 2 mobile Lighthouse budget gate.

Serves the exact review-branch HTML and verified national v2 dataset.
This deliberately does NOT represent authenticated WordPress/Divi staging.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import os

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/sprint2/college-search-national.v2.json.gz"
DATA_URL = "/data/sprint2/college-search-national.v2.json"


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path == DATA_URL:
            compressed = DATA.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(compressed)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(compressed)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        super().end_headers()


if __name__ == "__main__":
    os.chdir(ROOT)
    print("Sprint 2 mobile Lighthouse static proxy: http://127.0.0.1:8776/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8776), Handler).serve_forever()
