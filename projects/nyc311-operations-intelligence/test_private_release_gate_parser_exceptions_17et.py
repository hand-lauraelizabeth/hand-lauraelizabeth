"""Adversarial strict-JSON parser exception tests: every invalid input yields a HOLD report."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import private_release_gate as gate


class ParserExceptionFailClosedTests(unittest.TestCase):
    def _assert_hold(self, payload, source="candidate"):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files = {name: root / (name + ".json")
                     for name in ("candidate", "previous", "evidence")}
            for file in files.values():
                file.write_text("{}", encoding="utf-8")
            files[source].write_text(payload, encoding="utf-8")
            report = root / "report.json"
            args = [str(files["candidate"]), "--report", str(report)]
            if source == "previous":
                args += ["--previous-json", str(files["previous"])]
            if source == "evidence":
                args += ["--marginal-evidence-json", str(files["evidence"])]
            with patch.object(gate, "audit_single") as single, \\
                 patch.object(gate, "audit_pair") as pair, \\
                 patch.object(gate, "audit_marginals") as marginal, \\
                 patch.object(gate, "audit_integer_feasibility") as integer:
                code = gate.main(args)
            self.assertEqual(code, 2)
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "HOLD")
            self.assertIs(data["release_authorized"], False)
            self.assertIs(data["manual_review_required"], True)
            self.assertEqual(data["codes"], ["INPUT_READ_OR_PARSE_FAILED_CLOSED"])
            single.assert_not_called()
            pair.assert_not_called()
            marginal.assert_not_called()
            integer.assert_not_called()
            self.assertNotIn("999999999999999999", report.read_text(encoding="utf-8"))

    def test_deeply_nested_candidate(self):
        self._assert_hold("[" * 12000 + "0" + "]" * 12000)

    def test_deeply_nested_previous(self):
        self._assert_hold("[" * 12000 + "0" + "]" * 12000, source="previous")

    def test_invalid_decimal_exponent_candidate(self):
        self._assert_hold('{"x":1e-999999999999999999999999999}')

    def test_invalid_decimal_exponent_previous(self):
        self._assert_hold('{"x":-1e-999999999999999999999999999}', source="previous")

    def test_invalid_decimal_exponent_evidence(self):
        self._assert_hold('{"coefficients":[[1e-999999999999999999999999999]]}',
                          source="evidence")

    def test_invalid_decimal_zero_exponent(self):
        self._assert_hold('{"x":0e-999999999999999999999999999}')


if __name__ == "__main__":
    unittest.main()
