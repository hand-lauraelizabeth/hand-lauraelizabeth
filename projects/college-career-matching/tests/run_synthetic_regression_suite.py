#!/usr/bin/env python3
"""Run the College + Career synthetic architecture and integration regressions."""
from __future__ import annotations
import sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
if __name__=="__main__":
 suite=unittest.TestSuite();loader=unittest.defaultTestLoader
 for name in ["test_synthetic_recommendation_architecture","test_integration_synthetic_modules","test_integration_career_pathway_chain","test_regression_semantic_fixes","test_career_preference_operators"]:suite.addTests(loader.loadTestsFromName(name))
 result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)
