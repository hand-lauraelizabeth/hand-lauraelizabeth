#!/usr/bin/env python3
"""Normalize SUNY STEP Transfer Path Planner pages into model-ready course evidence.

The adapter expects a captured/scraped table from an authoritative STEP planner page,
not synthetic data. It deliberately preserves course expressions rather than assuming
that every displayed string represents one interchangeable course.

Required input columns:
    path_id, pathinst, campus_name, path_name, core_course, campus_course, source_url
Optional:
    notes, retrieved_at

Outputs:
    suny_transfer_path_plan.csv
    suny_transfer_path_course_option.csv
    suny_transfer_path_plan_qa.csv

Important semantic rule:
"No Course Identified" is coverage evidence, not a course and not a failure of the
path itself. It remains explicit in the plan table and produces no course option.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
from pathlib import Path
from typing import Iterable, List

NO_COURSE = "No Course Identified"


def read_csv(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Iterable[dict], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def stable_id(*parts: str) -> str:
    text = "|".join((p or "").strip() for p in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def norm_space(value: str) -> str:
    return " ".join((value or "").split())


def split_options(expr: str) -> List[str]:
    """Split explicit OR alternatives while preserving AND combinations.

    STEP examples include `MAT122 or MAT123` and `(BIO1550 and BIO.10)`.
    An AND expression is a required combination and must remain one option.
    """
    expr = norm_space(expr)
    if not expr or expr.casefold() == NO_COURSE.casefold():
        return []
    return [p.strip() for p in re.split(r"\s+or\s+", expr, flags=re.I) if p.strip()]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()

    rows = read_csv(args.input)
    required = {"path_id", "pathinst", "campus_name", "path_name", "core_course", "campus_course", "source_url"}
    missing = required - set(rows[0].keys() if rows else [])
    if missing:
        raise SystemExit(f"QA FAIL: missing columns: {sorted(missing)}")
    if not rows:
        raise SystemExit("QA FAIL: no Transfer Path Planner rows")

    plans = []
    options = []
    for r in rows:
        campus = norm_space(r["campus_name"])
        path_name = norm_space(r["path_name"])
        core = norm_space(r["core_course"])
        expr = norm_space(r["campus_course"])
        if not all((r["path_id"].strip(), r["pathinst"].strip(), campus, path_name, core, r["source_url"].strip())):
            raise SystemExit("QA FAIL: required value blank")

        plan_id = stable_id("SUNY", r["path_id"], r["pathinst"], core)
        identified = expr.casefold() != NO_COURSE.casefold() and bool(expr)
        plans.append({
            "path_plan_row_id": plan_id,
            "source_system": "SUNY",
            "path_id": r["path_id"].strip(),
            "pathinst": r["pathinst"].strip(),
            "campus_name_source": campus,
            "path_name_source": path_name,
            "core_course_source": core,
            "campus_course_expression": expr,
            "course_identified_flag": "1" if identified else "0",
            "notes": norm_space(r.get("notes", "")),
            "source_url": r["source_url"].strip(),
            "retrieved_at": r.get("retrieved_at", "").strip(),
        })
        for ordinal, option in enumerate(split_options(expr), start=1):
            options.append({
                "course_option_id": stable_id(plan_id, str(ordinal), option),
                "path_plan_row_id": plan_id,
                "option_ordinal": ordinal,
                "campus_course_option": option,
                "combination_required_flag": "1" if re.search(r"\s+and\s+", option, flags=re.I) else "0",
                "source_url": r["source_url"].strip(),
            })

    plan_fields = ["path_plan_row_id", "source_system", "path_id", "pathinst", "campus_name_source", "path_name_source", "core_course_source", "campus_course_expression", "course_identified_flag", "notes", "source_url", "retrieved_at"]
    option_fields = ["course_option_id", "path_plan_row_id", "option_ordinal", "campus_course_option", "combination_required_flag", "source_url"]
    write_csv(args.output_dir / "suny_transfer_path_plan.csv", plans, plan_fields)
    write_csv(args.output_dir / "suny_transfer_path_course_option.csv", options, option_fields)

    unique_plan_ids = len({r["path_plan_row_id"] for r in plans})
    no_course = sum(r["course_identified_flag"] == "0" for r in plans)
    multi_option = sum(1 for r in plans if len(split_options(r["campus_course_expression"])) > 1)
    combination = sum(r["combination_required_flag"] == "1" for r in options)
    qa = [{
        "planner_rows": len(plans),
        "unique_plan_rows": unique_plan_ids,
        "course_option_rows": len(options),
        "no_course_identified_rows": no_course,
        "multi_option_rows": multi_option,
        "combination_option_rows": combination,
        "unique_plan_id_check": "PASS" if unique_plan_ids == len(plans) else "FAIL",
    }]
    write_csv(args.output_dir / "suny_transfer_path_plan_qa.csv", qa, list(qa[0].keys()))

    if unique_plan_ids != len(plans):
        raise SystemExit("QA FAIL: duplicate deterministic path-plan row IDs")
    if any(o["path_plan_row_id"] not in {p["path_plan_row_id"] for p in plans} for o in options):
        raise SystemExit("QA FAIL: orphan course option")

    print(f"SUNY Transfer Path Planner: {len(plans)} rows; {len(options)} options; {no_course} no-course rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
