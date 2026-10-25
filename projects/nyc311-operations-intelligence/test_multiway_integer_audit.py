"""Synthetic adversarial checks for the unbound 20-cell multiway audit."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from multiway_integer_audit import audit


def sample():
    return {
        "schema_version": "nyc311-private-multiway-20-v1",
        "bounds": [[0, None] for _ in range(20)],
        "marginals": [
            {"cells": [0, 1], "total": 15},
            {"cells": [1, 2], "total": 13},
            {"cells": [0, 2], "total": 8},
        ],
        "targets": [0, 1, 2],
        "structural_zero_claims": [],
        "minimum_cell_count": 10,
    }


class MultiwayIntegerAuditTests(unittest.TestCase):
    def test_three_overlapping_pairs_force_two_small_integer_cells(self):
        findings = audit(sample())
        self.assertIn("small_multiway_target_forced_by_constraints", findings)
        self.assertIn("candidate_20cell_alignment_unverified", findings)
        self.assertIn("integer_multiway_feasibility_not_exhaustively_proven", findings)

    def test_fractional_linear_solution_rejected_for_integer_cells(self):
        p = sample()
        for marginal in p["marginals"]:
            marginal["total"] = 1
        self.assertIn("infeasible_multiway_integer_constraints", audit(p))

    def test_nonunique_pair_does_not_claim_unique_small_cell(self):
        p = sample()
        p["marginals"] = [{"cells": [0, 1], "total": 15}]
        p["targets"] = [0]
        findings = audit(p)
        self.assertIn("multiway_target_range_includes_small_cells", findings)
        self.assertNotIn("small_multiway_target_forced_by_constraints", findings)

    def test_claimed_structural_zero_not_assumed(self):
        p = sample()
        p["marginals"] = [{"cells": [0, 1], "total": 15}]
        p["targets"] = [0]
        p["structural_zero_claims"] = [0]
        findings = audit(p)
        self.assertIn("structural_zero_claims_not_authenticated", findings)
        self.assertIn("multiway_target_range_includes_small_cells", findings)
        self.assertNotIn("multiway_target_forced_by_constraints", findings)

    def test_contradictory_marginals_fail_closed(self):
        p = sample()
        p["marginals"] = [{"cells": [0, 1], "total": 10},
                          {"cells": [0], "total": 11}]
        self.assertIn("infeasible_multiway_constraints", audit(p))

    def test_conflicting_bound_fails_closed(self):
        p = sample()
        p["marginals"] = [{"cells": [0, 1], "total": 10}]
        p["bounds"][0] = [20, None]
        self.assertIn("infeasible_multiway_constraints", audit(p))

    def test_coverage_is_explicitly_incomplete(self):
        self.assertIn("incomplete_multiway_cell_coverage", audit(sample()))

    def test_full_20_cell_scope_does_not_certify_safety(self):
        p = sample()
        p["marginals"] = [{"cells": list(range(20)), "total": 200}]
        p["targets"] = [19]
        findings = audit(p)
        self.assertNotIn("incomplete_multiway_cell_coverage", findings)
        self.assertIn("multiway_target_range_includes_small_cells", findings)
        self.assertIn("candidate_20cell_alignment_unverified", findings)

    def test_exact_non_small_cell_still_never_approves(self):
        p = sample()
        p["marginals"] = [{"cells": [0], "total": 15}]
        p["targets"] = [0]
        findings = audit(p)
        self.assertIn("multiway_target_forced_by_constraints", findings)
        self.assertNotIn("small_multiway_target_forced_by_constraints", findings)
        self.assertIn("integer_multiway_feasibility_not_exhaustively_proven", findings)

    def test_invalid_schema_and_extra_field(self):
        p = sample()
        p["private_records"] = [1]
        self.assertEqual(audit(p), ["invalid_multiway_integer_schema"])

    def test_rejects_duplicate_scopes_and_duplicate_members(self):
        p = sample()
        p["marginals"].append({"cells": [1, 0], "total": 15})
        self.assertEqual(audit(p), ["invalid_multiway_integer_schema"])
        p = sample()
        p["marginals"][0]["cells"] = [0, 0]
        self.assertEqual(audit(p), ["invalid_multiway_integer_schema"])

    def test_rejects_bool_negative_and_non_integer_counts(self):
        for bad in (True, -1, 1.5):
            with self.subTest(bad=bad):
                p = sample()
                p["marginals"][0]["total"] = bad
                self.assertEqual(audit(p), ["invalid_multiway_integer_schema"])

    def test_rejects_bad_cell_indexes_and_bounds(self):
        p = sample()
        p["targets"] = [True]
        self.assertEqual(audit(p), ["invalid_multiway_integer_schema"])
        p = sample()
        p["bounds"][0] = [9, 8]
        self.assertEqual(audit(p), ["invalid_multiway_integer_schema"])

    def test_cli_never_echoes_input_totals_or_claims_approval(self):
        p = sample()
        p["marginals"] = [{"cells": [0], "total": 987654321}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.json"
            path.write_text(json.dumps(p), encoding="utf-8")
            run = subprocess.run([sys.executable,
                                  str(Path(__file__).with_name("multiway_integer_audit.py")),
                                  str(path)], capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2)
            report = json.loads(run.stdout)
            self.assertTrue(report["hold"])
            self.assertFalse(report["publication_approved"])
            self.assertNotIn("987654321", run.stdout)
            self.assertNotIn('"total"', run.stdout)

    def test_bounds_only_do_not_assert_structural_zero(self):
        p = sample()
        p["marginals"] = [{"cells": [0, 1], "total": 12}]
        p["targets"] = [0]
        p["structural_zero_claims"] = [0, 1]
        self.assertNotIn("multiway_target_forced_by_constraints", audit(p))


if __name__ == "__main__":
    unittest.main()
