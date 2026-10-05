#!/usr/bin/env python3
"""Run College + Career architecture, current-data, product, UI/service, and integration regressions."""
from __future__ import annotations
import sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
if __name__=="__main__":
 suite=unittest.TestSuite();loader=unittest.defaultTestLoader
 for name in ["test_synthetic_recommendation_architecture","test_integration_synthetic_modules","test_integration_career_pathway_chain","test_regression_semantic_fixes","test_career_preference_operators","test_current_college_product_adapters","test_affordability_outcomes_product_adapter","test_product_enrichment_governance","test_labor_market_product_bridge","test_labor_evidence_service_adapter","test_options_and_constraint_registry","test_candidate_detail_compare_service","test_prototype_contract_fixtures","test_product_snapshot_builder","test_product_snapshot_release_gate","test_match_service_adapter","test_ui_question_mapper","test_interface_options_builder"]:suite.addTests(loader.loadTestsFromName(name))
 result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)
