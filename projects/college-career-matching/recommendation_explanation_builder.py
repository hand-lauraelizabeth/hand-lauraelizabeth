#!/usr/bin/env python3
"""Build traceable, machine-readable recommendation explanations.

This layer does not invent prose or reasons from a final rank. It converts explicit
candidate evidence into reason/tradeoff/uncertainty records using a declarative
explanation policy.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

TRUE = {"1","true","yes","y"}
MISSING = {"","unknown","suppressed","not_pre_evaluated","unresolved_identity","not_published_for_geography","source_not_covered","field_absent_from_candidate_schema"}


def read(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None


def condition(value: str, op: str, threshold: str) -> bool:
    v = str(value).strip(); op = op.strip().lower(); t = str(threshold).strip()
    if op == "present": return v.lower() not in MISSING
    if op == "missing": return v.lower() in MISSING
    if op == "eq": return v == t
    if op == "neq": return v != t
    if op in {"gt","gte","lt","lte"}:
        a,b = num(v),num(t)
        if a is None or b is None: return False
        return {"gt":a>b,"gte":a>=b,"lt":a<b,"lte":a<=b}[op]
    raise ValueError(f"unsupported operator: {op}")


def build(candidates, policy, candidate_id):
    req = {"reason_code","dimension","field","operator","threshold","explanation_type","template"}
    if not req.issubset(policy.columns): raise ValueError(f"policy missing {sorted(req-set(policy.columns))}")
    if candidate_id not in candidates.columns: raise ValueError(f"missing {candidate_id}")
    if candidates[candidate_id].duplicated().any(): raise ValueError("candidate IDs must be unique")
    rows=[]
    for p in policy.itertuples(index=False):
        if p.field not in candidates.columns: continue
        for c in candidates.itertuples(index=False):
            d=c._asdict(); value=d[p.field]
            if condition(value,p.operator,p.threshold):
                rows.append({
                    candidate_id:d[candidate_id], "reason_code":p.reason_code,
                    "dimension":p.dimension, "explanation_type":p.explanation_type,
                    "field":p.field, "observed_value":value,
                    "message_template":p.template,
                    "source_field":getattr(p,"source_field", ""),
                    "vintage_field":getattr(p,"vintage_field", ""),
                    "specificity":getattr(p,"specificity", ""),
                    "priority":getattr(p,"priority", "")
                })
    detail=pd.DataFrame(rows)
    if detail.empty:
        detail=pd.DataFrame(columns=[candidate_id,"reason_code","dimension","explanation_type","field","observed_value","message_template","source_field","vintage_field","specificity","priority"])
    counts=(detail.groupby([candidate_id,"explanation_type"]).size().unstack(fill_value=0).reset_index()) if not detail.empty else pd.DataFrame({candidate_id:candidates[candidate_id]})
    return detail, counts


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidates",type=Path,required=True); ap.add_argument("--policy",type=Path,required=True)
    ap.add_argument("--candidate-id",default="candidate_id"); ap.add_argument("--out-dir",type=Path,required=True)
    a=ap.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
    detail,counts=build(read(a.candidates),read(a.policy),a.candidate_id)
    detail.to_csv(a.out_dir/"recommendation_explanation_evidence.csv",index=False)
    counts.to_csv(a.out_dir/"recommendation_explanation_coverage.csv",index=False)
    summary={"candidate_count":len(read(a.candidates)),"explanation_record_count":len(detail),"reason_code_count":detail.reason_code.nunique() if not detail.empty else 0,"status":"STRUCTURED_EVIDENCE_ONLY","note":"Audience-facing prose must be rendered from these traceable records, not inferred post-hoc from rank."}
    (a.out_dir/"recommendation_explanation_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

if __name__=="__main__": main()
