"""Normalize SUNY Transfer Path and Core Course snapshots for the College + Career Matching Tool.

This adapter consumes locally captured authoritative SUNY STEP exports/snapshots. It does
not silently scrape pages at runtime. The source snapshot, retrieval date, and source URL
must be supplied so builds remain reproducible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd


def norm_text(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def stable_id(*parts: object, prefix: str) -> str:
    key = "|".join((norm_text(p) or "").casefold() for p in parts)
    return f"{prefix}_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"


def first_present(row: pd.Series, candidates: list[str]) -> str | None:
    lookup = {str(c).strip().casefold(): c for c in row.index}
    for candidate in candidates:
        actual = lookup.get(candidate.casefold())
        if actual is not None:
            value = norm_text(row[actual])
            if value is not None:
                return value
    return None


def normalize_paths(df: pd.DataFrame, source_url: str, retrieved_at: str) -> pd.DataFrame:
    records = []
    for _, row in df.iterrows():
        path_name = first_present(row, ["path_name", "transfer_path", "path", "discipline", "major"])
        if not path_name:
            continue
        source_id = first_present(row, ["transfer_path_id", "path_id", "id"])
        path_id = source_id or stable_id(path_name, prefix="suny_path")
        records.append({
            "transfer_path_id": path_id,
            "source_system": "SUNY",
            "path_name": path_name,
            "cip": first_present(row, ["cip", "cip_code"]),
            "policy_guarantee": first_present(row, ["policy_guarantee", "guarantee", "transfer_guarantee"])
                or "SUNY Transfer Path Core Courses are guaranteed to transfer into aligned path majors subject to SUNY policy conditions.",
            "required_credits": first_present(row, ["required_credits", "credits"]),
            "source_url": source_url,
            "retrieved_at": retrieved_at,
        })
    return pd.DataFrame(records)


def normalize_core_courses(df: pd.DataFrame, source_url: str, retrieved_at: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    core = []
    campus = []
    for _, row in df.iterrows():
        core_name = first_present(row, ["core_course", "core_course_name", "course_name", "title"])
        universal_code = first_present(row, ["universal_code", "core_code", "code"])
        if not core_name and not universal_code:
            continue
        core_id = stable_id(universal_code, core_name, prefix="suny_core")
        core.append({
            "core_course_id": core_id,
            "source_system": "SUNY",
            "universal_code": universal_code,
            "core_course_name": core_name,
            "course_description": first_present(row, ["course_description", "description"]),
            "minimum_grade": first_present(row, ["minimum_grade", "min_grade"]) or "C",
            "source_url": source_url,
            "retrieved_at": retrieved_at,
        })

        campus_name = first_present(row, ["campus", "campus_name", "institution"])
        campus_course = first_present(row, ["campus_course", "campus_course_code", "local_course", "course_code"])
        if campus_name and campus_course:
            campus.append({
                "core_course_id": core_id,
                "institution_source_id": campus_name,
                "unitid": None,
                "course_code": campus_course,
                "course_title": first_present(row, ["campus_course_title", "local_course_title"]),
                "core_requirement_label": core_name,
                "minimum_grade": first_present(row, ["minimum_grade", "min_grade"]) or "C",
                "source_url": source_url,
                "retrieved_at": retrieved_at,
            })
    core_df = pd.DataFrame(core).drop_duplicates(subset=["core_course_id"] if core else None)
    campus_df = pd.DataFrame(campus).drop_duplicates() if campus else pd.DataFrame()
    return core_df, campus_df


def qa_report(paths: pd.DataFrame, core: pd.DataFrame, campus: pd.DataFrame) -> dict:
    return {
        "transfer_paths": int(len(paths)),
        "unique_transfer_path_ids": int(paths["transfer_path_id"].nunique()) if not paths.empty else 0,
        "core_courses": int(len(core)),
        "unique_core_course_ids": int(core["core_course_id"].nunique()) if not core.empty else 0,
        "campus_core_course_mappings": int(len(campus)),
        "distinct_campuses": int(campus["institution_source_id"].nunique()) if not campus.empty else 0,
        "campus_mappings_missing_unitid": int(campus["unitid"].isna().sum()) if not campus.empty else 0,
        "duplicate_campus_core_mappings": int(campus.duplicated().sum()) if not campus.empty else 0,
    }


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--paths", type=Path, required=True)
    p.add_argument("--core-courses", type=Path, required=True)
    p.add_argument("--source-url", required=True)
    p.add_argument("--retrieved-at", required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    paths = normalize_paths(read_table(args.paths), args.source_url, args.retrieved_at)
    core, campus = normalize_core_courses(read_table(args.core_courses), args.source_url, args.retrieved_at)
    paths.to_csv(args.output_dir / "transfer_path.csv", index=False)
    core.to_csv(args.output_dir / "core_course.csv", index=False)
    campus.to_csv(args.output_dir / "transfer_path_course.csv", index=False)
    (args.output_dir / "transfer_path_qa.json").write_text(json.dumps(qa_report(paths, core, campus), indent=2))


if __name__ == "__main__":
    main()
