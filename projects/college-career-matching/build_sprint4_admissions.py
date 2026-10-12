"""Enrich the existing national College Search score overlay with verified quartiles.

Never infer percentile bands from SAT_AVG or ACTCMMID. The pinned official June
2026 College Scorecard archive is SHA-256 validated before use. SAT composite
bands below are approximated by summing separately reported reading and math
section percentiles; these sums are NOT official composite-score percentiles.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "data/national/manifest.v1.json"
OVERLAY = ROOT / "data/sprint3/college-search-scores.v1.json"
BUDGET_BYTES = 750 * 1024
NATIONAL_GZIP_BYTES = 259736
SOURCE_BASE = "https://ed-public-download.scorecard.network/downloads/"


def numeric(value):
    if value in (None, "", "NULL", "PrivacySuppressed", "PS", "NA", "-3"):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return int(parsed) if parsed.is_integer() else None


def ordered(values, minimum, maximum):
    return (len(values) == 3 and all(
        isinstance(x, int) and minimum <= x <= maximum for x in values
    ) and values[0] <= values[1] <= values[2])


def main():
    manifest = json.loads(MANIFEST.read_text())
    overlay = json.loads(OVERLAY.read_text())
    assert manifest["source_release"] == "2026-06-10"
    assert overlay["source_archive_sha256"] == manifest["source_archive_sha256"]
    assert overlay["school_count"] == 6243
    filename = "Most-Recent-Cohorts-Institution_06102026.zip"
    # Try only ED-controlled hosts. The SHA-256 pin is mandatory regardless of
    # which hostname responds. An unavailable archive must fail closed.
    urls = [
        SOURCE_BASE + filename,
        "https://collegescorecard.ed.gov/data/" + filename,
        "https://ed-public-download.app.cloud.gov/downloads/" + filename,
    ]
    archive = None
    failures = []
    for url in urls:
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; CollegeSearchDataValidation/1.0)",
                "Accept": "application/zip,*/*",
            })
            with urllib.request.urlopen(request, timeout=120) as response:
                candidate = response.read()
            if hashlib.sha256(candidate).hexdigest() != manifest["source_archive_sha256"]:
                raise ValueError("Source archive checksum mismatch")
            archive = candidate
            break
        except (OSError, ValueError) as error:
            failures.append(f"{url}: {type(error).__name__}: {error}")
    if archive is None:
        raise RuntimeError("Could not download checksum-verified archive: " + " | ".join(failures))
    digest = hashlib.sha256(archive).hexdigest()

    records = overlay["institutions"]
    relevant = set(records)
    # The source shard universe includes many institutions with no test data.
    for shard in manifest["shards"]:
        shard_data = json.loads((ROOT / "data/national" / shard["file"]).read_text())
        relevant.update(row[0] for row in shard_data["records"])
    assert len(relevant) == 6243

    counts = {"sat_complete_bands": 0, "act_complete_bands": 0}
    seen = set()
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        candidates = [x for x in bundle.namelist() if x.lower().endswith(".csv")]
        if len(candidates) != 1:
            raise ValueError("Expected exactly one CSV in pinned source archive")
        with bundle.open(candidates[0]) as handle:
            lines = io.TextIOWrapper(handle, encoding="utf-8-sig", errors="strict", newline="")
            reader = csv.DictReader(lines)
            needed = ["UNITID", "SATVR25", "SATVR50", "SATVR75", "SATMT25",
                      "SATMT50", "SATMT75", "ACTCM25", "ACTCM50", "ACTCM75"]
            if not set(needed).issubset(reader.fieldnames or []):
                raise ValueError("June 2026 source lacks expected percentile columns")
            for row in reader:
                uid = str(row["UNITID"]).strip()
                if uid not in relevant:
                    continue
                if uid in seen:
                    raise ValueError("Duplicate UNITID in source")
                seen.add(uid)

                sat_verbal = [numeric(row["SATVR" + part]) for part in ("25", "50", "75")]
                sat_math = [numeric(row["SATMT" + part]) for part in ("25", "50", "75")]
                sat = [a + b for a, b in zip(sat_verbal, sat_math)] \
                    if ordered(sat_verbal, 200, 800) and ordered(sat_math, 200, 800) else [None] * 3
                act = [numeric(row["ACTCM" + part]) for part in ("25", "50", "75")]
                if not ordered(act, 1, 36):
                    act = [None] * 3
                if sat[0] is not None:
                    counts["sat_complete_bands"] += 1
                if act[0] is not None:
                    counts["act_complete_bands"] += 1
                existing = records.get(uid, [None, None])
                if sat[0] is not None or act[0] is not None or existing[0] is not None or existing[1] is not None:
                    records[uid] = existing[:2] + sat + act

    if len(seen) != 6243:
        raise ValueError(f"Source coverage incomplete: {len(seen)} of 6243")
    if min(counts.values()) < 100:
        raise ValueError("Unexpectedly few complete percentile rows; review source columns")
    overlay["institutions"] = dict(sorted(records.items()))
    overlay["percentile_source_status"] = "verified_2026_scorecard"
    overlay["percentile_source_fields"] = [
        "SATVR25", "SATVR50", "SATVR75", "SATMT25", "SATMT50", "SATMT75",
        "ACTCM25", "ACTCM50", "ACTCM75"
    ]
    overlay["percentile_interpretation"] = {
        "sat": "Approximate composite band; sum of independent verbal and math section percentiles",
        "act": "Reported ACT composite percentiles",
        "category": "Only a broad comparison to enrolled students; not an admission probability"
    }
    overlay["verified_band_counts"] = counts

    raw = json.dumps(overlay, ensure_ascii=False, separators=(",", ":")).encode()
    zipped = gzip.compress(raw, compresslevel=9, mtime=0)
    if NATIONAL_GZIP_BYTES + len(zipped) > BUDGET_BYTES:
        raise ValueError("Compressed national and overlay assets exceed 750 KiB budget")
    OVERLAY.write_bytes(raw)
    print(json.dumps({"pass": True, "source_zip_sha256": digest, "schools": len(relevant),
                      "verified_bands": counts, "overlay_gzip_bytes": len(zipped),
                      "total_estimated_gzip_bytes": NATIONAL_GZIP_BYTES + len(zipped),
                      "limit_bytes": BUDGET_BYTES}, sort_keys=True))


if __name__ == "__main__":
    main()
