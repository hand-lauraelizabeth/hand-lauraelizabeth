#!/usr/bin/env python3
"""Normalize CUNY Transfer Explorer course-to-major applicability evidence.

This layer deliberately separates:
1) course equivalency,
2) systemwide/course attributes (Major Gateway, Universal Transfer, Pathways), and
3) application to a specific receiving program requirement.

Inputs are saved authoritative T-Rex snapshots/exports, not runtime scraping.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
from pathlib import Path
from typing import Iterable, List


def clean(v: str) -> str:
    return " ".join((v or "").split())


def norm(v: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(v).lower()).strip()


def sid(*parts: str) -> str:
    raw = "|".join(norm(p) for p in parts)
    return "CUNY-MAJOR-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def read(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write(path: Path, rows: Iterable[dict], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def get(row: dict, *aliases: str) -> str:
    lowered = {norm(k): v for k, v in row.items()}
    for a in aliases:
        if norm(a) in lowered and clean(lowered[norm(a)]):
            return clean(lowered[norm(a)])
    return ""


def normalize(rows: List[dict], source_url: str, retrieved_at: str) -> List[dict]:
    out = []
    for r in rows:
        college = get(r, "college", "receiving college", "institution")
        program = get(r, "program", "major", "program name", "major name")
        program_id = get(r, "program id", "program_id", "major id", "major_id")
        degree = get(r, "degree", "degree type", "award")
        block = get(r, "requirement block", "block", "requirement group", "section")
        rule = get(r, "requirement", "rule", "requirement text", "rule text")
        course = get(r, "course", "course code", "receiving course")
        course_id = get(r, "course id", "course_id", "receiving course id")
        credits = get(r, "credits", "credit requirement")
        min_grade = get(r, "minimum grade", "min grade", "grade requirement")
        logic = get(r, "logic", "operator", "choice logic")
        if not logic:
            # Do not infer AND/OR from punctuation. Only recognize explicit source text.
            upper_rule = f" {rule.upper()} "
            if " OR " in upper_rule:
                logic = "OR"
            elif " AND " in upper_rule:
                logic = "AND"
        requirement_type = get(r, "requirement type", "type") or "source_defined"

        out.append({
            "major_applicability_id": sid(college, program_id or program, block, rule, course_id or course),
            "source_system": "CUNY_TREX",
            "receiving_institution_source_id": college,
            "receiving_unitid": "",
            "receiving_program_source_id": program_id,
            "receiving_program_name": program,
            "degree": degree,
            "requirement_block": block,
            "requirement_type": requirement_type,
            "requirement_rule_text": rule,
            "course_source_id": course_id,
            "course_code_or_label": course,
            "choice_logic": logic,
            "credits": credits,
            "minimum_grade": min_grade,
            "source_url": source_url,
            "retrieved_at": retrieved_at,
            "evidence_status": "source_observed",
        })
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-file", required=True, type=Path)
    p.add_argument("--source-url", required=True)
    p.add_argument("--retrieved-at", required=True)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    rows = normalize(read(args.source_file), args.source_url, args.retrieved_at)
    fields = [
        "major_applicability_id","source_system","receiving_institution_source_id","receiving_unitid",
        "receiving_program_source_id","receiving_program_name","degree","requirement_block","requirement_type",
        "requirement_rule_text","course_source_id","course_code_or_label","choice_logic","credits","minimum_grade",
        "source_url","retrieved_at","evidence_status"
    ]
    write(args.output, rows, fields)
    if not rows:
        raise SystemExit("QA FAIL: no major-applicability records")
    if len({r['major_applicability_id'] for r in rows}) != len(rows):
        raise SystemExit("QA FAIL: duplicate deterministic applicability IDs")
    if any(not r['receiving_program_name'] and not r['receiving_program_source_id'] for r in rows):
        raise SystemExit("QA FAIL: applicability row missing receiving program identity")
    print(f"CUNY major applicability: {len(rows)} rows normalized")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
