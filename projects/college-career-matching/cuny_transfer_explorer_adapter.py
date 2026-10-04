#!/usr/bin/env python3
"""Normalize public CUNY Transfer Explorer (T-Rex) course-equivalency snapshots.

The adapter is snapshot-first: extraction from the live site is deliberately
separate from normalization so raw evidence can be hashed/versioned. It
preserves directional, compound, and major-applicability semantics rather than
flattening them into a binary 'transfers' flag.

Input CSV (one row per observed equivalency expression):
 source_course_id, source_college, source_subject, source_course_code,
 source_course_title, receiving_college, receiving_course_expression,
 receiving_course_title, source_credits, receiving_credits,
 applicability_tags, minimum_grade, rule_notes, source_url, retrieved_at

A source_course_id should be taken from the stable numeric ID in T-Rex's
/course-transfer/<id>/... or equivalent receiving-course URL when available.
"""
from __future__ import annotations

import argparse, csv, hashlib, re
from pathlib import Path
from typing import Iterable, List

SYSTEM = "CUNY_TREX"


def clean(v: str) -> str:
    return " ".join((v or "").split())


def stable_id(*parts: str) -> str:
    key = "|".join(clean(p).lower() for p in parts)
    return "CUNY-TREX-" + hashlib.sha256(key.encode()).hexdigest()[:18]


def expression_type(expr: str) -> str:
    x = clean(expr).lower()
    if not x:
        return "unresolved"
    has_and = bool(re.search(r"\band\b|\+", x))
    has_or = bool(re.search(r"\bor\b", x))
    if has_and and has_or:
        return "compound_boolean"
    if has_and:
        return "and_combination"
    if has_or:
        return "or_alternatives"
    return "single_course"


def parse_tags(value: str):
    tags = [clean(t) for t in re.split(r"[;|]", value or "") if clean(t)]
    lower = " | ".join(t.lower() for t in tags)
    return {
        "tags": "; ".join(tags),
        "major_gateway_flag": "major gateway" in lower,
        "universal_transfer_flag": "universal transfer" in lower,
        "required_core_flag": "required core" in lower,
        "flexible_core_flag": "flexible core" in lower,
    }


def read(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write(path: Path, rows: Iterable[dict], fields: List[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def normalize(row: dict) -> dict:
    sid = clean(row.get("source_course_id", ""))
    src_college = clean(row.get("source_college", ""))
    src_code = clean(row.get("source_course_code", ""))
    recv_college = clean(row.get("receiving_college", ""))
    recv_expr = clean(row.get("receiving_course_expression", ""))
    tags = parse_tags(row.get("applicability_tags", ""))
    return {
        "equivalency_id": stable_id(sid, src_college, src_code, recv_college, recv_expr),
        "source_system": SYSTEM,
        "source_course_id": sid,
        "sending_institution_source_id": src_college,
        "sending_unitid": "",
        "sending_subject": clean(row.get("source_subject", "")),
        "sending_course_code": src_code,
        "sending_course_title": clean(row.get("source_course_title", "")),
        "sending_credits": clean(row.get("source_credits", "")),
        "receiving_institution_source_id": recv_college,
        "receiving_unitid": "",
        "receiving_course_expression": recv_expr,
        "receiving_course_title": clean(row.get("receiving_course_title", "")),
        "receiving_credits": clean(row.get("receiving_credits", "")),
        "expression_type": expression_type(recv_expr),
        "applicability_tags": tags["tags"],
        "major_gateway_flag": str(tags["major_gateway_flag"]).lower(),
        "universal_transfer_flag": str(tags["universal_transfer_flag"]).lower(),
        "required_core_flag": str(tags["required_core_flag"]).lower(),
        "flexible_core_flag": str(tags["flexible_core_flag"]).lower(),
        "minimum_grade": clean(row.get("minimum_grade", "")),
        "rule_notes": clean(row.get("rule_notes", "")),
        "source_url": clean(row.get("source_url", "")),
        "retrieved_at": clean(row.get("retrieved_at", "")),
        "evidence_status": "source_observed",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-file", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--qa-output", required=True, type=Path)
    a = p.parse_args()
    raw = read(a.source_file)
    out = [normalize(r) for r in raw]
    if not out: raise SystemExit("QA FAIL: no T-Rex equivalencies")
    if any(not r["source_course_id"] for r in out): raise SystemExit("QA FAIL: missing T-Rex source course ID")
    if any(not r["sending_institution_source_id"] or not r["receiving_institution_source_id"] for r in out):
        raise SystemExit("QA FAIL: missing directional institution")
    ids = [r["equivalency_id"] for r in out]
    if len(ids) != len(set(ids)): raise SystemExit("QA FAIL: duplicate deterministic equivalency IDs")
    fields = list(out[0])
    write(a.output, out, fields)
    counts = {}
    for r in out: counts[r["expression_type"]] = counts.get(r["expression_type"], 0) + 1
    qa = [{"records": len(out), "distinct_sending": len({r['sending_institution_source_id'] for r in out}),
           "distinct_receiving": len({r['receiving_institution_source_id'] for r in out}),
           "single_course": counts.get("single_course",0), "and_combination": counts.get("and_combination",0),
           "or_alternatives": counts.get("or_alternatives",0), "compound_boolean": counts.get("compound_boolean",0),
           "unresolved_expression": counts.get("unresolved",0)}]
    write(a.qa_output, qa, list(qa[0]))
    print(f"CUNY T-Rex: normalized {len(out)} directional equivalency expressions")
    return 0

if __name__ == "__main__": raise SystemExit(main())
