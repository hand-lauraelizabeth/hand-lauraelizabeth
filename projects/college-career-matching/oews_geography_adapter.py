"""Normalize May 2025 BLS OEWS state, metropolitan, and nonmetropolitan estimates.

This adapter keeps geography evidence separate from occupation projections and
from institution location. It expects official BLS OEWS downloadable data that
have already been captured locally. No geography is inferred from names.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

AREA_TYPES = {"1": "state", "4": "metropolitan_or_nonmetropolitan"}
KEEP = [
    "AREA", "AREA_TITLE", "AREA_TYPE", "PRIM_STATE", "NAICS", "NAICS_TITLE",
    "I_GROUP", "OWN_CODE", "OCC_CODE", "OCC_TITLE", "O_GROUP", "TOT_EMP",
    "EMP_PRSE", "JOBS_1000", "LOC_QUOTIENT", "PCT_TOTAL", "PCT_RPT",
    "H_MEAN", "A_MEAN", "MEAN_PRSE", "H_PCT10", "H_PCT25", "H_MEDIAN",
    "H_PCT75", "H_PCT90", "A_PCT10", "A_PCT25", "A_MEDIAN", "A_PCT75",
    "A_PCT90", "ANNUAL", "HOURLY",
]

def clean_code(value):
    if pd.isna(value): return None
    return str(value).strip()

def normalize(frame: pd.DataFrame, source_level: str) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(c).strip().upper() for c in frame.columns]
    required = {"AREA", "AREA_TITLE", "OCC_CODE", "OCC_TITLE"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required OEWS columns: {sorted(missing)}")
    cols = [c for c in KEEP if c in frame.columns]
    out = frame[cols].copy()
    out["AREA"] = out["AREA"].map(clean_code)
    out["OCC_CODE"] = out["OCC_CODE"].map(clean_code)
    out["source_level"] = source_level
    out["oews_vintage"] = "May 2025"
    out["geography_key"] = out["source_level"] + ":" + out["AREA"].fillna("")
    out["occupation_geography_key"] = out["geography_key"] + ":" + out["OCC_CODE"].fillna("")
    return out

def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path, low_memory=False)

def coverage(out: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for level, g in out.groupby("source_level", dropna=False):
        rows.append({
            "source_level": level,
            "rows": len(g),
            "areas": g["AREA"].nunique(dropna=True),
            "occupations": g["OCC_CODE"].nunique(dropna=True),
            "area_occupation_pairs": g["occupation_geography_key"].nunique(),
            "duplicate_area_occupation_pairs": int(g["occupation_geography_key"].duplicated().sum()),
            "missing_area": int(g["AREA"].isna().sum()),
            "missing_occupation": int(g["OCC_CODE"].isna().sum()),
        })
    return pd.DataFrame(rows)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", type=Path)
    p.add_argument("--area", type=Path)
    p.add_argument("--outdir", type=Path, required=True)
    args = p.parse_args()
    parts = []
    if args.state: parts.append(normalize(read_table(args.state), "state"))
    if args.area: parts.append(normalize(read_table(args.area), "metro_nonmetro"))
    if not parts: raise SystemExit("Supply --state and/or --area official OEWS file")
    out = pd.concat(parts, ignore_index=True, sort=False)
    args.outdir.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.outdir / "oews_2025_geography_occupation.csv", index=False)
    coverage(out).to_csv(args.outdir / "oews_2025_geography_coverage.csv", index=False)
    if out["AREA"].isna().any() or out["OCC_CODE"].isna().any():
        raise SystemExit("QA failure: missing geography or occupation keys")

if __name__ == "__main__":
    main()
