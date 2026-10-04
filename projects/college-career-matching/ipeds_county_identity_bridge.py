#!/usr/bin/env python3
"""Build a conservative UNITID -> current county GEOID bridge.

Inputs
------
IPEDS HD directory CSV (HD2024 or later compatible extract)
Census county/county-equivalent reference CSV

The bridge prefers IPEDS COUNTYCD when it is a valid five-digit county GEOID.
County names are retained for QA, not used to silently repair a missing/invalid code.
Geographic vintages are explicit because county-equivalent definitions can change.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd


def clean_code(value, width):
    if pd.isna(value):
        return ""
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(width) if s.isdigit() else ""


def build_bridge(ipeds: pd.DataFrame, counties: pd.DataFrame, ipeds_vintage: str, census_vintage: str):
    required = {"UNITID", "INSTNM", "STABBR", "COUNTYCD", "COUNTYNM"}
    missing = required - set(ipeds.columns)
    if missing:
        raise ValueError(f"IPEDS input missing required columns: {sorted(missing)}")

    c = counties.copy()
    # Accept either a ready GEOID or Census STATEFP + COUNTYFP.
    if "GEOID" in c.columns:
        c["county_geoid"] = c["GEOID"].map(lambda x: clean_code(x, 5))
    elif {"STATEFP", "COUNTYFP"}.issubset(c.columns):
        c["county_geoid"] = c["STATEFP"].map(lambda x: clean_code(x, 2)) + c["COUNTYFP"].map(lambda x: clean_code(x, 3))
    else:
        raise ValueError("County reference requires GEOID or STATEFP + COUNTYFP")

    county_name_col = next((x for x in ["COUNTYNAME", "NAME", "NAMELSAD"] if x in c.columns), None)
    if county_name_col is None:
        c["census_county_name"] = ""
    else:
        c["census_county_name"] = c[county_name_col].fillna("").astype(str).str.strip()

    ref = c[["county_geoid", "census_county_name"]].drop_duplicates("county_geoid")
    out = ipeds[["UNITID", "INSTNM", "STABBR", "COUNTYCD", "COUNTYNM"]].copy()
    out["unitid"] = out["UNITID"].map(lambda x: clean_code(x, 6))
    out["county_geoid"] = out["COUNTYCD"].map(lambda x: clean_code(x, 5))
    out = out.merge(ref, on="county_geoid", how="left", validate="m:1")
    out["county_identity_status"] = "resolved"
    out.loc[out["county_geoid"].eq(""), "county_identity_status"] = "missing_ipeds_county_code"
    out.loc[out["county_geoid"].ne("") & out["census_county_name"].isna(), "county_identity_status"] = "county_code_not_in_reference_vintage"
    out["ipeds_vintage"] = ipeds_vintage
    out["census_county_vintage"] = census_vintage
    out["match_method"] = "ipeds_countycd_to_census_geoid"
    out["source_county_name"] = out["COUNTYNM"].fillna("").astype(str).str.strip()
    out["county_name_review_flag"] = (
        out["county_identity_status"].eq("resolved")
        & out["source_county_name"].str.casefold().ne(out["census_county_name"].fillna("").str.casefold())
    )
    return out[["unitid","INSTNM","STABBR","county_geoid","source_county_name","census_county_name","county_identity_status","county_name_review_flag","match_method","ipeds_vintage","census_county_vintage"]]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ipeds", required=True)
    p.add_argument("--counties", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--ipeds-vintage", default="HD2024")
    p.add_argument("--census-vintage", default="current")
    a = p.parse_args()
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    bridge = build_bridge(pd.read_csv(a.ipeds, dtype=str), pd.read_csv(a.counties, dtype=str), a.ipeds_vintage, a.census_vintage)
    bridge.to_csv(out_dir / "institution_county_identity.csv", index=False)
    qa = pd.DataFrame([
        {"metric":"institutions","value":len(bridge)},
        {"metric":"resolved","value":int(bridge.county_identity_status.eq("resolved").sum())},
        {"metric":"missing_ipeds_county_code","value":int(bridge.county_identity_status.eq("missing_ipeds_county_code").sum())},
        {"metric":"county_code_not_in_reference_vintage","value":int(bridge.county_identity_status.eq("county_code_not_in_reference_vintage").sum())},
        {"metric":"county_name_review_flags","value":int(bridge.county_name_review_flag.sum())},
    ])
    qa.to_csv(out_dir / "institution_county_identity_qa.csv", index=False)
    if bridge.unitid.eq("").any() or bridge.unitid.duplicated().any():
        raise SystemExit("QA failure: missing or duplicate UNITID")

if __name__ == "__main__":
    main()
