#!/usr/bin/env python3
"""QA and deterministic rendering for recommendation explanation records.

Consumes structured reason records, review queue, and optional stability output.
It does not generate persuasive free-form explanations. It validates support,
flags contradictions, and emits a stable JSON payload for a UI renderer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd

ALLOWED_KINDS = {"support", "tradeoff", "uncertainty", "condition", "context", "review"}
NEGATIVE_EVIDENCE_STATES = {"unknown", "suppressed", "not_pre_evaluated", "unresolved_identity", "not_published_for_geography", "source_not_covered", "insufficient_evidence"}


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def require(df: pd.DataFrame, cols: list[str], label: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{label} missing columns: {missing}")


def truthy(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def qa_and_render(reasons: pd.DataFrame, reviews: pd.DataFrame, stability: pd.DataFrame | None, candidate_id: str):
    require(reasons, [candidate_id, "reason_code", "reason_kind", "dimension", "claim_text", "evidence_state", "source_family", "source_vintage", "specificity"], "reasons")
    if reasons.duplicated([candidate_id, "reason_code"]).any():
        raise ValueError("duplicate candidate/reason_code records")
    bad_kinds = sorted(set(reasons["reason_kind"]) - ALLOWED_KINDS)
    if bad_kinds:
        raise ValueError(f"unsupported reason_kind values: {bad_kinds}")

    if reviews.empty:
        reviews = pd.DataFrame(columns=[candidate_id, "dimension", "field", "review_reason"])
    else:
        require(reviews, [candidate_id, "dimension", "field", "review_reason"], "review queue")

    stability_lookup = {}
    if stability is not None and not stability.empty:
        require(stability, [candidate_id, "best_rank", "worst_rank", "rank_range", "top_k_persistence"], "stability")
        stability_lookup = stability.set_index(candidate_id).to_dict("index")

    qa_rows = []
    payloads = []
    for cid, group in reasons.groupby(candidate_id, sort=True):
        issues = []
        kinds = set(group["reason_kind"])

        # Support/tradeoff claims require affirmative evidence, not absence/unknown states.
        unsupported = group[group["reason_kind"].isin(["support", "tradeoff"]) & group["evidence_state"].str.lower().isin(NEGATIVE_EVIDENCE_STATES)]
        for r in unsupported.itertuples():
            issues.append(("unsupported_directional_claim", r.reason_code, r.dimension))

        # Material claims require source lineage.
        material = group[group["reason_kind"].isin(["support", "tradeoff", "condition"])]
        no_source = material[material["source_family"].str.strip().eq("")]
        for r in no_source.itertuples():
            issues.append(("missing_source_lineage", r.reason_code, r.dimension))

        # A reason code cannot be both positive and negative for the same candidate/dimension.
        for dim, dg in group.groupby("dimension"):
            codes_by_kind = {k: set(dg.loc[dg["reason_kind"].eq(k), "reason_code"]) for k in ["support", "tradeoff"]}
            overlap = codes_by_kind["support"] & codes_by_kind["tradeoff"]
            for code in sorted(overlap):
                issues.append(("contradictory_reason_kind", code, dim))

        candidate_reviews = reviews[reviews[candidate_id].eq(cid)]
        for r in candidate_reviews.itertuples(index=False):
            issues.append(("open_review_trigger", getattr(r, "field"), getattr(r, "dimension")))

        qa_status = "BLOCK" if issues else "PASS"
        for issue_type, code, dim in issues:
            qa_rows.append({candidate_id: cid, "qa_status": "BLOCK", "issue_type": issue_type, "reason_or_field": code, "dimension": dim})
        if not issues:
            qa_rows.append({candidate_id: cid, "qa_status": "PASS", "issue_type": "", "reason_or_field": "", "dimension": ""})

        def records(kind: str):
            cols = ["reason_code", "dimension", "claim_text", "evidence_state", "source_family", "source_vintage", "specificity"]
            extra = [c for c in ["source_url", "conditions", "evidence_strength"] if c in group.columns]
            return group.loc[group["reason_kind"].eq(kind), cols + extra].to_dict("records")

        payload = {
            "candidate_id": cid,
            "render_status": "blocked_for_review" if qa_status == "BLOCK" else "renderable",
            "why_it_matches": records("support"),
            "tradeoffs": records("tradeoff"),
            "conditions": records("condition"),
            "what_we_dont_know": records("uncertainty"),
            "context": records("context"),
            "review_notes": records("review"),
            "stability": stability_lookup.get(cid, None),
            "qa_issue_count": len(issues),
        }
        payloads.append(payload)

    qa = pd.DataFrame(qa_rows)
    summary = {
        "candidate_count": len(payloads),
        "renderable_candidates": sum(p["render_status"] == "renderable" for p in payloads),
        "blocked_candidates": sum(p["render_status"] != "renderable" for p in payloads),
        "qa_issue_count": int((qa["issue_type"] != "").sum()) if not qa.empty else 0,
        "rule": "Blocked candidates retain their evidence payload for review but should not be presented as validated recommendations."
    }
    return qa, payloads, summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--reasons", type=Path, required=True)
    p.add_argument("--reviews", type=Path)
    p.add_argument("--stability", type=Path)
    p.add_argument("--candidate-id", default="candidate_id")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    reviews = read(args.reviews) if args.reviews else pd.DataFrame()
    stability = read(args.stability) if args.stability else None
    qa, payloads, summary = qa_and_render(read(args.reasons), reviews, stability, args.candidate_id)
    qa.to_csv(args.out_dir / "recommendation_explanation_qa.csv", index=False)
    (args.out_dir / "recommendation_explanation_payload.json").write_text(json.dumps(payloads, indent=2), encoding="utf-8")
    (args.out_dir / "recommendation_explanation_qa_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
