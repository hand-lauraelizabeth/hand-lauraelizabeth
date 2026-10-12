"""Build and validate the Sprint 1 national College Search data assets."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data" / "national"
TARGET = ROOT / "data" / "sprint1"
JSON_PATH = TARGET / "college-search-national.v1.json"
GZIP_PATH = TARGET / "college-search-national.v1.json.gz"

def expected():
    manifest = json.loads((SOURCE / "manifest.v1.json").read_text(encoding="utf-8"))
    assert manifest["source_release"] == "2026-06-10"
    assert manifest["expected_records"] == 6243
    schools = {}
    total = 0
    missing_urls = 0
    for shard in manifest["shards"]:
        raw = (SOURCE / shard["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == shard["sha256"], shard["file"]
        records = json.loads(raw)["records"]
        assert len(records) == shard["count"], shard["file"]
        for row in records:
            unitid, name, city, state = row[:4]
            url = row[19] or None
            assert isinstance(unitid, str) and len(unitid) in (6, 8) and unitid.isdigit()
            assert unitid not in schools, unitid
            assert all(isinstance(v, str) and v.strip() for v in (name, city, state))
            assert len(state) == 2
            assert url is None or url.lower().startswith(("https://", "http://"))
            schools[unitid] = {"name": name, "city": city, "state": state, "url": url}
            missing_urls += int(url is None)
            total += 1
    assert total == 6243 and len(schools) == 6243
    return {"source": "College Scorecard", "source_release": "2026-06-10",
            "institutions": dict(sorted(schools.items()))}, missing_urls

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify JSON, gzip and all source shards")
    args = parser.parse_args()
    expected_data, missing = expected()
    if args.check:
        raw = JSON_PATH.read_bytes()
        assert json.loads(raw) == expected_data, "Keyed JSON does not match the verified source"
        compressed = GZIP_PATH.read_bytes()
        assert gzip.decompress(compressed) == raw, "Gzip does not round-trip to the original JSON"
    else:
        TARGET.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(expected_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        JSON_PATH.write_bytes(raw)
        compressed = gzip.compress(raw, compresslevel=9, mtime=0)
        GZIP_PATH.write_bytes(compressed)
    summary = {"passed": True, "count": len(expected_data["institutions"]),
               "missing_urls": missing, "json_bytes": len(raw),
               "gzip_bytes": len(compressed), "gzip_kiB": round(len(compressed)/1024, 2),
               "json_sha256": hashlib.sha256(raw).hexdigest(),
               "gzip_sha256": hashlib.sha256(compressed).hexdigest()}
    assert len(compressed) < 500 * 1024, "Gzip payload exceeds 500 KiB budget"
    print(json.dumps(summary, sort_keys=True))

if __name__ == "__main__":
    main()
