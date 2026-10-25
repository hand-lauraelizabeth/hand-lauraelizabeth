"""Adversarial synthetic-only exact-integer disclosure tests."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from overlap_integer_audit import audit


def sample():
    return {"schema_version": "nyc311-private-overlap-2x2-v1",
            "row_totals": [22, 9], "column_totals": [11, 20],
            "bounds": [[[0, None], [20, None]],
                       [[0, None], [0, None]]],
            "targets": [[0, 0]], "minimum_cell_count": 10}


class OverlapIntegerAuditTests(unittest.TestCase):
    def test_nonnegative_integer_bounds_reconstruct_small_target(self):
        findings = audit(sample())
        self.assertIn("small_integer_target_uniquely_reconstructible", findings)

    def test_without_lower_bound_target_not_unique(self):
        p = sample()
        p["bounds"][0][1][0] = 0
        findings = audit(p)
        self.assertNotIn("integer_target_uniquely_reconstructible", findings)
        self.assertIn("integer_target_range_includes_small_cells", findings)

    def test_explicit_known_zero_can_fix_target(self):
        p = sample()
        p["bounds"][1][1] = [0, 0]
        self.assertIn("integer_target_uniquely_reconstructible", audit(p))

    def test_infeasible_constraints_fail_closed(self):
        p = sample()
        p["bounds"][0][1] = [25, None]
        self.assertEqual(audit(p), ["infeasible_overlap_constraints"])

    def test_totals_must_agree(self):
        p = sample()
        p["column_totals"][1] += 1
        self.assertEqual(audit(p), ["inconsistent_overlap_totals"])

    def test_boolean_not_accepted_as_integer(self):
        for key in ("row_totals", "column_totals"):
            p = sample()
            p[key][0] = True
            self.assertEqual(audit(p), ["invalid_overlap_integer_schema"])

    def test_boolean_bound_and_threshold_rejected(self):
        p = sample()
        p["bounds"][0][0][0] = True
        self.assertEqual(audit(p), ["invalid_overlap_integer_schema"])
        p = sample()
        p["minimum_cell_count"] = True
        self.assertEqual(audit(p), ["invalid_overlap_integer_schema"])

    def test_duplicate_and_out_of_range_targets_rejected(self):
        for targets in ([[0, 0], [0, 0]], [[2, 0]], [[True, 0]], []):
            p = sample()
            p["targets"] = targets if targets == [] else ([targets] if isinstance(targets[0], int) else targets)
            self.assertEqual(audit(p), ["invalid_overlap_integer_schema"])

    def test_no_unexpected_record_fields(self):
        p = sample()
        p["incident_address"] = "synthetic"
        self.assertEqual(audit(p), ["invalid_overlap_integer_schema"])

    def test_large_counts_exact_no_float_rounding(self):
        p = sample()
        shift = 10**18
        p["row_totals"][0] += shift
        p["column_totals"][1] += shift
        p["bounds"][0][1][0] += shift
        self.assertIn("small_integer_target_uniquely_reconstructible", audit(p))

    def test_multiple_targets_do_not_emit_counts(self):
        p = sample()
        p["targets"] = [[0, 0], [1, 0], [1, 1]]
        self.assertIn("integer_target_uniquely_reconstructible", audit(p))
        self.assertNotIn("2", json.dumps(audit(p)))

    def test_cli_fail_closed_and_no_private_values_echoed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "private.json"
            path.write_text(json.dumps(sample()), encoding="utf-8")
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("overlap_integer_audit.py")), str(path)],
                                    text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            report = json.loads(result.stdout)
            self.assertTrue(report["hold"])
            self.assertFalse(report["publication_approved"])
            self.assertNotIn('"row_totals"', result.stdout)
            self.assertNotIn('"22"', result.stdout)

    def test_invalid_json_cli(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "private.json"
            path.write_text("{broken", encoding="utf-8")
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("overlap_integer_audit.py")), str(path)],
                                    text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("unreadable_or_invalid_overlap_constraints", result.stdout)


if __name__ == "__main__":
    unittest.main()
