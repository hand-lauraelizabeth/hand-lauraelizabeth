"""Build College Search v3: v2 fields + verified cost/net price/tuition.

Reuses SHA-pinned June 2026 College Scorecard 13-shard source. Keeps exact keys
and source data, null for unavailable figures, and deterministic gzip <=750KiB.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from collections import Counter

from build_sprint2_national import ROOT, SOURCE, build as build_v2, BUDGET_BYTES

DEST=ROOT/"data/sprint3"
JSON_PATH=DEST/"college-search-national.v3.json"
GZIP_PATH=DEST/"college-search-national.v3.json.gz"
EXPECTED={"annual_cost":5022,"average_net_price":5021,"tuition_in_state":3601,"tuition_out_state":3601}

def money(value,uid,field):
    if value is None:return None
    if type(value) is not int or value<0:
        raise ValueError(f"Invalid {field} for {uid}: {value!r}")
    return value

def build():
    old,_,_=build_v2()
    schools=old["institutions"]
    seen=set()
    manifest=json.loads((SOURCE/"manifest.v1.json").read_text())
    assert manifest["row_layout"][8:12]==["tuition_in","tuition_out","annual_cost","net_price"]
    for shard in manifest["shards"]:
        path=SOURCE/shard["file"]
        raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==shard["sha256"]
        records=json.loads(raw)["records"]
        assert len(records)==shard["count"]
        for row in records:
            uid=row[0]
            if uid in seen or uid not in schools:raise ValueError(f"Missing or duplicate {uid}")
            seen.add(uid)
            r=schools[uid]
            r["tuition_in_state"]=money(row[8],uid,"tuition_in")
            r["tuition_out_state"]=money(row[9],uid,"tuition_out")
            r["annual_cost"]=money(row[10],uid,"annual_cost")
            r["average_net_price"]=money(row[11],uid,"net_price")
    assert len(seen)==len(schools)==6243
    coverage={k:sum(v[k] is not None for v in schools.values()) for k in EXPECTED}
    assert coverage==EXPECTED,coverage
    return old,coverage

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="store_true")
    args=p.parse_args()
    doc,coverage=build()
    raw=json.dumps(doc,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    packed=gzip.compress(raw,compresslevel=9,mtime=0)
    assert len(packed)<=BUDGET_BYTES,f"v3 browser data is too large {len(packed)} > {BUDGET_BYTES}"
    if args.check:
        assert JSON_PATH.read_bytes()==raw,"v3 data drift"
        assert GZIP_PATH.read_bytes()==packed,"v3 gzip drift"
        assert gzip.decompress(packed)==raw
    else:
        DEST.mkdir(parents=True,exist_ok=True)
        JSON_PATH.write_bytes(raw)
        GZIP_PATH.write_bytes(packed)
    print(json.dumps({
        "pass":True,"count":6243,"source_release":"2026-06-10",
        "coverage":coverage,"json_bytes":len(raw),"gzip_bytes":len(packed),
        "gzip_limit":BUDGET_BYTES,"gzip_headroom":BUDGET_BYTES-len(packed),
        "json_sha256":hashlib.sha256(raw).hexdigest(),
        "gzip_sha256":hashlib.sha256(packed).hexdigest(),
    },sort_keys=True))
if __name__=="__main__":
    main()
