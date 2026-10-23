"""Synthetic regression: nonzero JSON floats must not silently underflow to zero."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import private_release_gate as gate


class UnderflowGateTests(unittest.TestCase):
    def _run(self, payload, source="candidate", should_reject=True):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files = {name: root / (name + ".json")
                     for name in ("candidate", "previous", "evidence")}
            for path in files.values():
                path.write_text("{}", encoding="utf-8")
            files[source].write_text(payload, encoding="utf-8")
            report = root / "report.json"
            args = [str(files["candidate"]), "--report", str(report)]
            if source == "previous":
                args += ["--previous-json", str(files["previous"])]
            if source == "evidence":
                args += ["--marginal-evidence-json", str(files["evidence"])]
            with patch.object(gate, "audit_single") as single, \
                 patch.object(gate, "audit_pair") as pair, \
                 patch.object(gate, "audit_marginals") as marginal, \
                 patch.object(gate, "audit_integer_feasibility") as integer:
                exit_code = gate.main(args)
            self.assertEqual(exit_code, 2)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "HOLD")
            self.assertIs(result["release_authorized"], False)
            self.assertIs(result["manual_review_required"], True)
            self.assertNotIn("1e-9999", report.read_text(encoding="utf-8"))
            if should_reject:
                self.assertIn("INPUT_READ_OR_PARSE_FAILED_CLOSED", result["codes"])
                single.assert_not_called()
                pair.assert_not_called()
                marginal.assert_not_called()
                integer.assert_not_called()
            else:
                self.assertNotIn("INPUT_READ_OR_PARSE_FAILED_CLOSED", result["codes"])
                if source == "candidate":
                    single.assert_called_once()

    def test_positive_nonzero_underflow(self):
        self._run('{"count":1e-9999}')

    def test_negative_nonzero_underflow(self):
        self._run('{"count":-1e-9999}')

    def test_near_subnormal_boundary_underflow(self):
        self._run('{"count":2e-324}')

    def test_nested_array_underflow(self):
        self._run('{"groups":[{"weight":3e-9999}]}')

    def test_previous_snapshot_underflow(self):
        self._run('{"source_rows":1e-9999}', source="previous")

    def test_marginal_evidence_underflow(self):
        self._run('{"coefficients":[[1e-9999]],"totals":[1],"suppressed":[0]}',
                  source="evidence")

    def test_true_zero_exponent_is_valid(self):
        self._run('{"count":0e-9999,"other":-0.000e-9999}',
                  should_reject=False)

    def test_smallest_subnormal_is_preserved(self):
        self._run('{"count":5e-324}', should_reject=False)


if __name__ == "__main__":
    unittest.main()
