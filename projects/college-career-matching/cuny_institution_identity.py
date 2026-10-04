#!/usr/bin/env python3
"""Resolve CUNY Transfer Explorer college labels to IPEDS UNITIDs.

Conservative identity layer for T-Rex. Exact/reviewed aliases may be accepted;
ambiguous, system-level, or non-degree identities remain review/unresolved.
"""
from __future__ import annotations
import argparse, csv, re, unicodedata
from pathlib import Path
from typing import Dict, List

# T-Rex public college labels observed 2026-10-04. Targets are IPEDS-style names;
# aliases remain version controlled and should be reviewed against the current HD file.
ALIASES: Dict[str, str] = {
    "baruch college": "CUNY Bernard M Baruch College",
    "borough of manhattan cc": "CUNY Borough of Manhattan Community College",
    "bronx cc": "CUNY Bronx Community College",
    "brooklyn college": "CUNY Brooklyn College",
    "city college": "CUNY City College",
    "college of staten island": "CUNY College of Staten Island",
    "guttman cc": "CUNY Stella and Charles Guttman Community College",
    "hostos cc": "CUNY Hostos Community College",
    "hunter college": "CUNY Hunter College",
    "john jay college": "CUNY John Jay College of Criminal Justice",
    "kingsborough cc": "CUNY Kingsborough Community College",
    "laguardia cc": "CUNY LaGuardia Community College",
    "lehman college": "CUNY Lehman College",
    "medgar evers college": "CUNY Medgar Evers College",
    "nyc college of technology": "CUNY New York City College of Technology",
    "queens college": "CUNY Queens College",
    "queensborough cc": "CUNY Queensborough Community College",
    "school of labor urban studies": "CUNY School of Labor and Urban Studies",
    "school of professional studies": "CUNY School of Professional Studies",
    "york college": "CUNY York College",
}

def norm(v: str) -> str:
    v = unicodedata.normalize("NFKD", v or "")
    v = "".join(c for c in v if not unicodedata.combining(c)).lower().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", v).split())

def read(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f: return list(csv.DictReader(f))

def write(path: Path, rows: List[dict], fields: List[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--trex-colleges", required=True, type=Path)
    p.add_argument("--ipeds-hd", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    a=p.parse_args()
    src, hd=read(a.trex_colleges), read(a.ipeds_hd)
    ny=[r for r in hd if (r.get("STABBR") or "").upper()=="NY"]
    idx={}
    for r in ny: idx.setdefault(norm(r.get("INSTNM","")), []).append(r)
    out=[]
    for s in src:
        label=(s.get("college_name") or s.get("institution_name") or "").strip()
        target=ALIASES.get(norm(label), label)
        candidates=idx.get(norm(target), [])
        if len(candidates)==1:
            c=candidates[0]; status="accepted"; method="reviewed_alias_ny" if norm(label) in ALIASES else "exact_name_ny"
            unitid=c.get("UNITID",""); ipeds=c.get("INSTNM",""); note=""
        elif len(candidates)>1:
            status="review"; method="ambiguous_name_ny"; unitid=ipeds=""; note="Multiple NY IPEDS candidates; no automatic merge."
        else:
            status="unresolved"; method="unresolved"; unitid=ipeds=""; note="No evidence-qualified NY IPEDS match."
        out.append({"trex_college_name":label,"unitid":unitid,"ipeds_name":ipeds,"match_method":method,"match_status":status,"candidate_count":len(candidates),"source_url":s.get("source_url",""),"review_note":note})
    fields=["trex_college_name","unitid","ipeds_name","match_method","match_status","candidate_count","source_url","review_note"]
    write(a.output_dir/"cuny_institution_identity.csv",out,fields)
    write(a.output_dir/"cuny_institution_identity_review.csv",[r for r in out if r["match_status"]!="accepted"],fields)
    total=len(out); accepted=sum(r["match_status"]=="accepted" for r in out); review=sum(r["match_status"]=="review" for r in out); unresolved=total-accepted-review
    cov=[{"source_colleges":total,"accepted_matches":accepted,"review_candidates":review,"unresolved":unresolved,"accepted_match_rate":round(accepted/total,6) if total else 0}]
    write(a.output_dir/"cuny_institution_identity_coverage.csv",cov,["source_colleges","accepted_matches","review_candidates","unresolved","accepted_match_rate"])
    if any(not r["trex_college_name"] for r in out): raise SystemExit("QA FAIL: blank T-Rex college label")
    if any(r["match_status"]=="accepted" and (not r["unitid"] or r["candidate_count"]!=1) for r in out): raise SystemExit("QA FAIL: invalid accepted identity")
    print(f"CUNY identity: {accepted}/{total} accepted; {review} review; {unresolved} unresolved")
if __name__=="__main__": main()
