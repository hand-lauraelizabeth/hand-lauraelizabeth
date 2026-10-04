#!/usr/bin/env python3
"""Synthetic regression tests for core recommendation semantics.

All institutions, programs, occupations, values, and preferences here are fictional.
The tests exercise architecture/guardrails, not empirical recommendation quality.
"""
from __future__ import annotations
import unittest

MISSING={"","NA","N/A","NULL","NONE","UNKNOWN","SUPPRESSED","UNRESOLVED_IDENTITY","SOURCE_NOT_COVERED","NOT_PRE_EVALUATED"}

def constraint(value,target,unknown_policy="retain"):
    if str(value).strip().upper() in MISSING:
        return "excluded_unknown_by_explicit_policy" if unknown_policy=="exclude" else "eligible_with_unknown"
    return "eligible" if str(value)==str(target) else "excluded"

def compose(values,weights,partial_policy):
    observed=[(v,w) for v,w in zip(values,weights) if v is not None]
    if len(observed)<len(values) and partial_policy=="block": return None,"partial_blocked"
    denom=sum(w for _,w in observed)
    return (sum(v*w for v,w in observed)/denom,"complete" if len(observed)==len(values) else "partial_renormalized") if denom else (None,"insufficient")

def explicit_weights(profile):
    active={d:i for d,i,explicit in profile if explicit}
    total=sum(active.values())
    return {d:i/total for d,i in active.items()} if total else {}

class SyntheticArchitectureTests(unittest.TestCase):
    def test_hard_constraint_exclusion(self):
        self.assertEqual(constraint("online","campus"),"excluded")

    def test_unknown_retained_by_default(self):
        self.assertEqual(constraint("UNKNOWN","campus"),"eligible_with_unknown")
        self.assertEqual(constraint("UNKNOWN","campus","exclude"),"excluded_unknown_by_explicit_policy")

    def test_missing_is_not_zero(self):
        value,status=compose([0.8,None],[1,1],"block")
        self.assertIsNone(value); self.assertEqual(status,"partial_blocked")

    def test_partial_renormalization_requires_policy(self):
        blocked=compose([0.8,None],[1,1],"block")
        allowed=compose([0.8,None],[1,1],"renormalize_observed")
        self.assertEqual(blocked,(None,"partial_blocked")); self.assertEqual(allowed,(0.8,"partial_renormalized"))

    def test_unspecified_dimensions_receive_no_weight(self):
        w=explicit_weights([("affordability",3,True),("career_pathway_fit",2,True),("college_fit",99,False)])
        self.assertNotIn("college_fit",w); self.assertAlmostEqual(w["affordability"],0.6); self.assertAlmostEqual(w["career_pathway_fit"],0.4)

    def test_many_to_many_pathways_remain_visible(self):
        pathways=[("FIC-CIP-A","FIC-SOC-1"),("FIC-CIP-A","FIC-SOC-2"),("FIC-CIP-A","FIC-SOC-3")]
        self.assertEqual(len([p for p in pathways if p[0]=="FIC-CIP-A"]),3)
        self.assertEqual(len(set(p[1] for p in pathways)),3)

    def test_release_gate_fail_closed_semantics(self):
        required_checks=[True,True,False]
        self.assertEqual("BLOCKED" if not all(required_checks) else "ELIGIBLE_FOR_REVIEW","BLOCKED")

    def test_dependency_failure_propagates(self):
        stage={"source":"PASS","normalize":"FAIL"}
        downstream="BLOCKED_BY_DEPENDENCY" if stage["normalize"]!="PASS" else "RUN"
        self.assertEqual(downstream,"BLOCKED_BY_DEPENDENCY")

if __name__=="__main__": unittest.main()
