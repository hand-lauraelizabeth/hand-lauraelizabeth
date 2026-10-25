"""Synthetic-only regression tests for public marginal residual reconstruction."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from external_marginal_audit import audit


def candidate(count=12, closed=0):
    return {
        "schema_version": "nyc311-review-candidate-v1", "dataset_id": "erm2-nwe9",
        "snapshot_as_of": "2026-10-25",
        "rules": {"grain": "month × borough × agency × original API complaint_type",
                  "display_minimum_cell_count": 10},
        "aggregates": [{"month": "2026-09", "borough": "QUEENS", "agency": "DOT",
                        "problem": "Fictional A", "requests": count,
                        "closed_with_valid_interval": closed}],
    }


def marginals(total=15):
    return {"dataset_id": "erm2-nwe9", "grain": "month × borough × agency",
            "totals": [{"month": "2026-09", "borough": "QUEENS", "agency": "DOT",
                        "requests": total}]}


class ExternalMarginalAudit(unittest.TestCase):
    def test_small_residual_reconstructible(self):
        self.assertIn("small_external_residual_reconstructible", audit(candidate(), marginals(15)))

    def test_residual_equal_threshold_is_not_certified_safe(self):
        result = audit(candidate(), marginals(22))
        self.assertNotIn("small_external_residual_reconstructible", result)
        self.assertIn("external_residual_may_reveal_suppressed_categories", result)

    def test_zero_residual_still_on_review_hold(self):
        result = audit(candidate(), marginals(12))
        self.assertNotIn("small_external_residual_reconstructible", result)
        self.assertIn("cross_table_and_auxiliary_inference_review_pending", result)

    def test_external_total_below_visible_sum(self):
        self.assertIn("external_total_below_visible_sum", audit(candidate(), marginals(11)))

    def test_missing_marginal_coverage(self):
        result = audit(candidate(), {**marginals(), "totals": []})
        self.assertIn("unverified_external_marginal_coverage", result)

    def test_marginal_with_no_visible_group(self):
        m = marginals()
        m["totals"][0]["agency"] = "NYPD"
        self.assertIn("external_marginal_without_visible_group", audit(candidate(), m))

    def test_duplicate_external_marginal(self):
        m = marginals()
        m["totals"].append(copy.deepcopy(m["totals"][0]))
        self.assertIn("duplicate_external_marginal", audit(candidate(), m))

    def test_rejects_negative_and_boolean_marginal_counts(self):
        for value in (-1, True):
            with self.subTest(value=value):
                self.assertIn("invalid_external_marginal_schema", audit(candidate(), marginals(value)))

    def test_rejects_unexpected_fields_and_wrong_grain(self):
        m = marginals()
        m["totals"][0]["incident_address"] = "Fictional only"
        self.assertIn("invalid_external_marginal_schema", audit(candidate(), m))
        m = marginals()
        m["grain"] = "wrong"
        self.assertIn("invalid_external_marginal_schema", audit(candidate(), m))

    def test_unsafe_candidate_cannot_be_certified(self):
        c = candidate(count=9)
        self.assertIn("invalid_or_unsafe_candidate", audit(c, marginals(12)))

    def test_multiple_visible_categories_are_summed(self):
        c = candidate()
        row = copy.deepcopy(c["aggregates"][0])
        row["problem"] = "Fictional B"
        row["requests"] = 12
        c["aggregates"].append(row)
        self.assertIn("small_external_residual_reconstructible", audit(c, marginals(27)))

    def test_cli_fails_closed_without_echoing_marginal_values(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / "candidate.json", Path(td) / "marginals.json"
            a.write_text(json.dumps(candidate()), encoding="utf-8")
            b.write_text(json.dumps(marginals(15)), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(Path(__file__).with_name("external_marginal_audit.py")), str(a), str(b)],
                                  text=True, capture_output=True, check=False)
            self.assertEqual(proc.returncode, 2)
            report = json.loads(proc.stdout)
            self.assertTrue(report["hold"])
            self.assertFalse(report["publication_approved"])
            self.assertIn("small_external_residual_reconstructible", report["findings"])
            self.assertNotIn('"requests"', proc.stdout)


if __name__ == "__main__":
    unittest.main()
