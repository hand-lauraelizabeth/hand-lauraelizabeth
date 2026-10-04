#!/usr/bin/env python3
"""Build a source-stable SUNY Transfer Path ↔ Core Course bridge.

Inputs
------
--core-master : normalized/exported STEP Core Course Master List containing at
least course_id and course; universal_code/active/url_key are retained when present.
--planner : normalized Transfer Path Planner rows containing pathid, pathinst,
core_course_name, equivalent_course_expression and source_url.

Outputs
-------
transfer_path_core_course.csv
transfer_path_core_course_review.csv
transfer_path_core_course_coverage.csv

The bridge prefers stable STEP course IDs (csid/course_id) over text labels. Text
matching is intentionally conservative and never silently guesses among duplicate
or ambiguous labels.
"""
from __future__ import annotations
import argparse, csv, hashlib, re, unicodedata
from pathlib import Path
from typing import Iterable, List, Dict


def norm(v: str) -> str:
    v = unicodedata.normalize("NFKD", v or "")
    v = "".join(c for c in v if not unicodedata.combining(c)).lower()
    v = v.replace("&", " and ")
    v = re.sub(r"[^a-z0-9]+", " ", v)
    return " ".join(v.split())


def read(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write(path: Path, rows: Iterable[dict], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def stable_id(*parts: str) -> str:
    return "suny_tpcc_" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


def first(row: dict, *names: str) -> str:
    for n in names:
        if (row.get(n) or "").strip(): return row[n].strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--core-master", required=True, type=Path)
    ap.add_argument("--planner", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    a = ap.parse_args()

    master = read(a.core_master); planner = read(a.planner)
    by_name: Dict[str, List[dict]] = {}
    by_id: Dict[str, dict] = {}
    for r in master:
        cid = first(r, "course_id", "csid", "Course ID")
        name = first(r, "course", "course_name", "Course")
        if cid: by_id[cid] = r
        if name: by_name.setdefault(norm(name), []).append(r)

    out=[]
    for p in planner:
        pathid=first(p,"pathid","path_id")
        pathinst=first(p,"pathinst","path_institution_id")
        pname=first(p,"core_course_name","core_course","Core Course")
        explicit=first(p,"csid","course_id","core_course_id")
        candidates=[]; method=""
        if explicit and explicit in by_id:
            candidates=[by_id[explicit]]; method="explicit_csid"
        elif pname:
            candidates=by_name.get(norm(pname),[]); method="exact_normalized_title"
        if len(candidates)==1:
            m=candidates[0]; status="matched"
            cid=first(m,"course_id","csid","Course ID")
            cname=first(m,"course","course_name","Course")
            ucode=first(m,"universal_code","Universal Code")
            active=first(m,"active","Active")
            note=""
        elif len(candidates)>1:
            status="review"; cid=cname=ucode=active=""
            note=f"{len(candidates)} Core Course Master List rows share this normalized title."
        else:
            status="unresolved"; cid=cname=ucode=active=""
            note="No exact Core Course Master List match; preserve planner text for review."
        out.append({
            "bridge_id":stable_id(pathid,pathinst,pname,first(p,"source_url")),
            "pathid":pathid,"pathinst":pathinst,
            "planner_core_course_name":pname,
            "core_course_id":cid,"core_course_name":cname,
            "universal_code":ucode,"core_course_active":active,
            "match_method":method or "none","match_status":status,
            "equivalent_course_expression":first(p,"equivalent_course_expression","equivalent_course","Equivalent Course"),
            "source_url":first(p,"source_url"),"review_note":note,
        })

    fields=["bridge_id","pathid","pathinst","planner_core_course_name","core_course_id","core_course_name","universal_code","core_course_active","match_method","match_status","equivalent_course_expression","source_url","review_note"]
    write(a.output_dir/"transfer_path_core_course.csv",out,fields)
    write(a.output_dir/"transfer_path_core_course_review.csv",[r for r in out if r["match_status"]!="matched"],fields)
    total=len(out); matched=sum(r["match_status"]=="matched" for r in out); review=sum(r["match_status"]=="review" for r in out); unresolved=sum(r["match_status"]=="unresolved" for r in out)
    coverage=[{"planner_rows":total,"matched_rows":matched,"review_rows":review,"unresolved_rows":unresolved,"match_rate":round(matched/total,6) if total else 0,"distinct_paths":len({r['pathid'] for r in out if r['pathid']}),"distinct_core_course_ids":len({r['core_course_id'] for r in out if r['core_course_id']})}]
    write(a.output_dir/"transfer_path_core_course_coverage.csv",coverage,list(coverage[0]))

    if not master: raise SystemExit("QA FAIL: empty Core Course Master List")
    if not planner: raise SystemExit("QA FAIL: empty Transfer Path Planner input")
    if any(not r["pathid"] for r in out): raise SystemExit("QA FAIL: planner row missing pathid")
    if len({r["bridge_id"] for r in out}) != len(out): raise SystemExit("QA FAIL: duplicate deterministic bridge IDs")
    if any(r["match_status"]=="matched" and not r["core_course_id"] for r in out): raise SystemExit("QA FAIL: matched row lacks stable Core Course ID")
    print(f"SUNY path-core bridge: {matched}/{total} matched; {review} review; {unresolved} unresolved")
    return 0

if __name__ == "__main__": raise SystemExit(main())
