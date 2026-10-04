#!/usr/bin/env python3
"""Build a deterministic county/county-equivalent -> May 2025 OEWS area bridge.

Inputs are authoritative BLS May 2025 area-definition records exported/captured as CSV/XLSX.
No city-name, institution-name, or fuzzy geography matching is permitted.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
import pandas as pd

REQUIRED = ["state_abbr", "county_name", "area_code", "area_name", "source_url"]


def clean(v):
    if pd.isna(v): return ""
    return re.sub(r"\s+", " ", str(v)).strip()


def stable_id(*parts):
    payload = "|".join(clean(x).lower() for x in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def read_table(path: Path):
    return pd.read_excel(path, dtype=str) if path.suffix.lower() in {".xlsx", ".xls"} else pd.read_csv(path, dtype=str)


def normalize(df: pd.DataFrame):
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing: raise ValueError(f"Missing required columns: {missing}")
    out = df.copy()
    for c in out.columns: out[c] = out[c].map(clean)
    out["state_abbr"] = out["state_abbr"].str.upper()
    out["area_type"] = out["area_name"].str.contains("nonmetropolitan", case=False, na=False).map({True:"nonmetropolitan", False:"metropolitan"})
    out["county_area_bridge_id"] = out.apply(lambda r: stable_id("2025-05", r["state_abbr"], r["county_name"], r["area_code"]), axis=1)
    out["oews_vintage"] = "2025-05"
    out["geography_match_method"] = "authoritative_bls_county_area_definition"
    out["cross_state_area_flag"] = out["area_name"].str.contains(r",.*-.*|-[A-Z]{2}(?:-|$)", regex=True, na=False)
    return out


def qa(out: pd.DataFrame):
    county_key = out["state_abbr"] + "|" + out["county_name"].str.lower()
    counts = county_key.value_counts()
    conflicts = out[county_key.isin(counts[counts > 1].index)].copy()
    # Duplicate identical rows are harmless but multiple distinct area codes for one county require review.
    distinct = out.groupby(["state_abbr","county_name"])["area_code"].nunique()
    ambiguous_keys = distinct[distinct > 1]
    return {
        "vintage":"2025-05",
        "rows":int(len(out)),
        "states_or_equivalents":int(out["state_abbr"].nunique()),
        "areas":int(out["area_code"].nunique()),
        "metropolitan_rows":int((out["area_type"]=="metropolitan").sum()),
        "nonmetropolitan_rows":int((out["area_type"]=="nonmetropolitan").sum()),
        "blank_area_codes":int((out["area_code"]=="").sum()),
        "blank_counties":int((out["county_name"]=="").sum()),
        "county_keys_with_multiple_distinct_area_codes":int(len(ambiguous_keys)),
        "duplicate_county_rows":int(len(conflicts)),
    }, conflicts


def main():
    p=argparse.ArgumentParser()
    p.add_argument("source", type=Path); p.add_argument("--outdir", type=Path, default=Path("out/oews_county_area"))
    a=p.parse_args(); a.outdir.mkdir(parents=True, exist_ok=True)
    out=normalize(read_table(a.source)); metrics, conflicts=qa(out)
    if metrics["rows"] == 0 or metrics["blank_area_codes"] or metrics["blank_counties"]: raise SystemExit(f"QA failure: {metrics}")
    if metrics["county_keys_with_multiple_distinct_area_codes"]: raise SystemExit(f"Ambiguous county->area assignments: {metrics}")
    cols=["county_area_bridge_id","state_abbr","county_name","area_code","area_name","area_type","cross_state_area_flag","oews_vintage","geography_match_method","source_url"]
    if "retrieved_at" in out.columns: cols.append("retrieved_at")
    out[cols].drop_duplicates().sort_values(["state_abbr","county_name"]).to_csv(a.outdir/"oews_county_area_bridge.csv", index=False)
    conflicts.to_csv(a.outdir/"oews_county_area_review.csv", index=False)
    (a.outdir/"oews_county_area_qa.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__": main()
