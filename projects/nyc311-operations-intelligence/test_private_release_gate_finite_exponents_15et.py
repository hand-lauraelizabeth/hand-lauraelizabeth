"""Synthetic regression: JSON exponent overflow must fail closed before auditing."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import private_release_gate as gate


class FiniteExponentGateTests(unittest.TestCase):
    def _reject(self, payload, *, source="candidate"):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate, previous, evidence = (root / "candidate.json",
                                             root / "previous.json",
                                             root / "evidence.json")
            report = root / "report.json"
            candidate.write_text("{}")
            previous.write_text("{}")
            evidence.write_text("{}")
            selected = {"candidate": candidate, "previous": previous,
                        "evidence": evidence}[source]
            selected.write_text(payload)
            args = [str(candidate), "--report", str(report)]
            if source == "previous":
                args += ["--previous-json", str(previous)]
            if source == "evidence":
                args += ["--marginal-evidence-json", str(evidence)]
            with patch.object(gate, "audit_single") as single, \
                 patch.object(gate, "audit_pair") as pair, \
                 patch.object(gate, "audit_marginals") as marginal:
                exit_code = gate.main(args)
            self.assertEqual(exit_code, 2)
            single.assert_not_called()
            pair.assert_not_called()
            marginal.assert_not_called()
            result = json.loads(report.read_text())
            self.assertEqual(result["status"], "HOLD")
            self.assertFalse(result["release_authorized"])
            self.assertIn("INPUT_READ_OR_PARSE_FAILED_CLOSED", result["codes"])
            self.assertNotIn("1e309", report.read_text())

    def test_positive_exponent_overflow(self):
        self._reject('{"source_rows":1e309}')

    def test_negative_exponent_overflow(self):
        self._reject('{"source_rows":-1e309}')

    def test_nested_array_exponent_overflow(self):
        self._reject('{"groups":[{"count":9.9e999}]}')

    def test_previous_snapshot_exponent_overflow(self):
        self._reject('{"quality":{"count":1e309}}', source="previous")

    def test_marginal_evidence_exponent_overflow(self):
        self._reject('{"coefficients":[[1e309]],"totals":[1],"suppressed":[0]}',
                     source="evidence")

    def test_finite_fraction_passes_parser_and_still_holds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate, report = root / "candidate.json", root / "report.json"
            candidate.write_text('{"rate":1.25,"large":1e308}')
            hold = {"status": "HOLD", "manual_review_required": True, "codes": []}
            with patch.object(gate, "audit_single", return_value=hold) as audit:
                self.assertEqual(gate.main([str(candidate), "--report", str(report)]), 2)
            audit.assert_called_once()
            self.assertEqual(audit.call_args.args[0]["rate"], 1.25)
            self.assertEqual(audit.call_args.args[0]["large"], 1e308)
            self.assertFalse(json.loads(report.read_text())["release_authorized"])


if __name__ == "__main__":
    unittest.main()
