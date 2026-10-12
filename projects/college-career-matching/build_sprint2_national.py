"""Build national College Search Sprint 2 data from verified June 2026 Scorecard shards.

Versioned v2 assets do NOT replace or modify the live Sprint 1 v1 dataset.
The size metric is the national source row's undergraduate enrollment field.
Unknown/unsupported values are represented by JSON null, never estimates.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data" / "national"
DEST = ROOT / "data" / "sprint2"
JSON_PATH = DEST / "college-search-national.v2.json"
GZIP_PATH = DEST / "college-search-national.v2.json.gz"
BUDGET_BYTES = 750 * 1024

CONTROL = {1: "public", 2: "private_nonprofit", 3: "private_for_profit"}
LOCALE = {
    **dict.fromkeys((11, 12, 13), "city"),
    **dict.fromkeys((21, 22, 23), "suburb"),
    **dict.fromkeys((31, 32, 33), "town"),
    **dict.fromkeys((41, 42, 43), "rural"),
}
EXPECTED_LAYOUT = ["unitid", "name", "city", "state", "control",
                   "predominant_degree", "highest_degree", "size",
                   "tuition_in", "tuition_out", "annual_cost", "net_price",
                   "income_net_prices", "admit_rate", "sat_avg", "act_mid",
                   "locale_code", "latitude", "longitude", "institution_url"]


def build():
    manifest = json.loads((SOURCE / "manifest.v1.json").read_text(encoding="utf-8"))
    assert manifest["source_release"] == "2026-06-10"
    assert manifest["expected_records"] == 6243
    assert manifest["row_layout"][:20] == EXPECTED_LAYOUT
    schools = {}
    invalid_locale_codes = Counter()
    unknown = Counter()
    for shard in manifest["shards"]:
        path = SOURCE / shard["file"]
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == shard["sha256"], path
        records = json.loads(raw)["records"]
        assert len(records) == shard["count"], path
        for row in records:
            assert len(row) >= 20, shard["file"]
            unitid, name, city, state = row[:4]
            if not (isinstance(unitid, str) and unitid.isdigit() and unitid not in schools):
                raise ValueError(f"Invalid/duplicate UNITID: {unitid!r}")
            assert all(isinstance(v, str) and v.strip() for v in (name, city, state))
            assert len(state) == 2
            control = CONTROL.get(row[4])
            locale = LOCALE.get(row[16])
            size = row[7]
            if not (size is None or (type(size) is int and size >= 0)):
                raise ValueError(f"Unexpected undergraduate size for {unitid}: {size!r}")
            url = row[19] or None
            assert url is None or (isinstance(url, str) and
                                   url.lower().startswith(("https://", "http://")))
            schools[unitid] = {
                "name": name, "city": city, "state": state, "url": url,
                "control": control, "locale": locale,
                "undergraduate_size": size,
            }
            if control is None:
                unknown["control"] += 1
            if locale is None:
                unknown["locale"] += 1
                if row[16] is not None:
                    invalid_locale_codes[str(row[16])] += 1
            if size is None:
                unknown["undergraduate_size"] += 1
    assert len(schools) == 6243, len(schools)
    assert unknown["control"] == 0
    assert unknown["locale"] == 531 and dict(invalid_locale_codes) == {"2": 1, "-3": 3}
    assert unknown["undergraduate_size"] == 781
    return {
        "source": "College Scorecard",
        "source_release": "2026-06-10",
        "institutions": dict(sorted(schools.items())),
    }, unknown, invalid_locale_codes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="Validate committed JSON, gzip and all 13 source shard hashes")
    args = parser.parse_args()
    document, unknown, invalid_codes = build()
    raw = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    assert len(compressed) <= BUDGET_BYTES, (
        f"Sprint 2 gzip {len(compressed)} bytes exceeds {BUDGET_BYTES} byte budget"
    )
    if args.check:
        assert JSON_PATH.read_bytes() == raw, "Committed v2 JSON differs from verified source"
        assert GZIP_PATH.read_bytes() == compressed, "Committed v2 gzip not deterministic"
        assert gzip.decompress(GZIP_PATH.read_bytes()) == raw, "Gzip roundtrip failed"
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        JSON_PATH.write_bytes(raw)
        GZIP_PATH.write_bytes(compressed)
    summary = {
        "passed": True, "mode": "check" if args.check else "build",
        "records": len(document["institutions"]),
        "source_release": document["source_release"],
        "unknown": dict(sorted(unknown.items())),
        "nonstandard_locale_codes_treated_as_unknown": dict(sorted(invalid_codes.items())),
        "json_bytes": len(raw), "gzip_bytes": len(compressed),
        "gzip_kiB": round(len(compressed) / 1024, 2),
        "gzip_limit_kiB": BUDGET_BYTES // 1024,
        "gzip_headroom_bytes": BUDGET_BYTES - len(compressed),
        "json_sha256": hashlib.sha256(raw).hexdigest(),
        "gzip_sha256": hashlib.sha256(compressed).hexdigest(),
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
