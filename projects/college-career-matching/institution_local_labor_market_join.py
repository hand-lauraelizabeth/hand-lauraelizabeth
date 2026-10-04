#!/usr/bin/env python3
"""Join institutions to May 2025 OEWS local occupation evidence.

Expected inputs are normalized outputs from the upstream contracts:
1. institution_county.csv: UNITID, county_geoid, county_identity_status
2. county_oews_area.csv: county_geoid, oews_area_code, area_title, area_type
3. oews_local_occupation.csv: oews_area_code, occ_code plus OEWS measures

The join never substitutes state or national evidence for missing local evidence.
Missing geography and suppressed OEWS estimates remain explicit coverage states.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

SUPPRESSION_TOKENS = {"#", "**", "*", "—", "-", "NA", "N/A"}


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _require(df: pd.DataFrame, cols: list[str], label: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {missing}")


def _present(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str).str.strip()
    return s.ne("") & ~s.isin(SUPPRESSION_TOKENS)


def build(inst: pd.DataFrame, county_area: pd.DataFrame, oews: pd.DataFrame):
    _require(inst, ["UNITID", "county_geoid"], "institution county")
    _require(county_area, ["county_geoid", "oews_area_code"], "county-area")
    _require(oews, ["oews_area_code", "occ_code"], "OEWS local occupation")

    # One institution row should remain one institution through the geography join.
    if inst["UNITID"].duplicated().any():
        raise ValueError("institution county input contains duplicate UNITID values")
    if county_area["county_geoid"].duplicated().any():
        raise ValueError("county-area input contains duplicate county_geoid values")

    geo = inst.merge(county_area, on="county_geoid", how="left", indicator="_area_join")
    geo["local_area_resolved_flag"] = geo["_area_join"].eq("both") & geo["oews_area_code"].ne("")
    geo["local_area_coverage_status"] = "resolved"
    geo.loc[geo["county_geoid"].eq(""), "local_area_coverage_status"] = "missing_county"
    geo.loc[geo["county_geoid"].ne("") & ~geo["local_area_resolved_flag"], "local_area_coverage_status"] = "county_not_mapped_to_oews_area"

    joined = geo.merge(oews, on="oews_area_code", how="left", indicator="_occupation_join", suffixes=("", "_oews"))
    joined["occupation_local_evidence_flag"] = joined["_occupation_join"].eq("both")

    measure_candidates = [c for c in ["tot_emp", "a_mean", "a_median", "h_mean", "h_median", "loc_quotient"] if c in joined.columns]
    if measure_candidates:
        present = pd.concat([_present(joined[c]) for c in measure_candidates], axis=1).any(axis=1)
        joined["published_local_measure_flag"] = joined["occupation_local_evidence_flag"] & present
        joined["local_measure_status"] = "published"
        joined.loc[~joined["occupation_local_evidence_flag"], "local_measure_status"] = "occupation_not_published_for_area"
        joined.loc[joined["occupation_local_evidence_flag"] & ~present, "local_measure_status"] = "all_selected_measures_suppressed_or_missing"
    else:
        joined["published_local_measure_flag"] = joined["occupation_local_evidence_flag"]
        joined["local_measure_status"] = joined["occupation_local_evidence_flag"].map({True: "occupation_record_present", False: "occupation_not_published_for_area"})

    institution_coverage = (
        geo.groupby(["local_area_coverage_status"], dropna=False)["UNITID"]
        .nunique().reset_index(name="institution_count")
    )

    resolved_units = int(geo.loc[geo["local_area_resolved_flag"], "UNITID"].nunique())
    total_units = int(geo["UNITID"].nunique())
    occupation_rows = joined.loc[joined["occupation_local_evidence_flag"]].copy()
    published_rows = joined.loc[joined["published_local_measure_flag"]].copy()

    qa = pd.DataFrame([
        {"metric": "institutions_total", "value": total_units},
        {"metric": "institutions_local_area_resolved", "value": resolved_units},
        {"metric": "institutions_local_area_unresolved", "value": total_units - resolved_units},
        {"metric": "institution_local_area_coverage_rate", "value": round(resolved_units / total_units, 6) if total_units else 0},
        {"metric": "institution_occupation_rows", "value": len(occupation_rows)},
        {"metric": "institution_occupation_rows_with_published_selected_measure", "value": len(published_rows)},
        {"metric": "distinct_local_occupations", "value": occupation_rows["occ_code"].nunique() if not occupation_rows.empty else 0},
        {"metric": "distinct_oews_areas_reached", "value": geo.loc[geo["local_area_resolved_flag"], "oews_area_code"].nunique()},
    ])
    return geo.drop(columns=["_area_join"]), joined.drop(columns=["_area_join", "_occupation_join"]), institution_coverage, qa


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--institution-county", type=Path, required=True)
    p.add_argument("--county-area", type=Path, required=True)
    p.add_argument("--oews-local", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    geo, joined, coverage, qa = build(_read(args.institution_county), _read(args.county_area), _read(args.oews_local))
    geo.to_csv(args.out_dir / "institution_local_labor_market.csv", index=False)
    joined.to_csv(args.out_dir / "institution_local_occupation_evidence.csv", index=False)
    coverage.to_csv(args.out_dir / "institution_local_labor_market_coverage.csv", index=False)
    qa.to_csv(args.out_dir / "institution_local_labor_market_qa.csv", index=False)


if __name__ == "__main__":
    main()
