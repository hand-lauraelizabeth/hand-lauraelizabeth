"""Bounded-input regression tests for the integrated private NYC 311 gate."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import private_release_gate as gate


class BoundedJSONGateTests(unittest.TestCase):
    def _hold_for_input(self, source, payload, limit=32):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / "candidate.json"
            previous = root / "previous.json"
            evidence = root / "evidence.json"
            report = root / "report.json"
            files = {"candidate": candidate, "previous": previous, "evidence": evidence}
            for path in files.values():
                path.write_bytes(b"{}")
            files[source].write_bytes(payload)
            args = [str(candidate), "--report", str(report)]
            if source == "previous":
                args.extend(["--previous-json", str(previous)])
            if source == "evidence":
                args.extend(["--marginal-evidence-json", str(evidence)])
            with patch.object(gate, "MAX_INPUT_BYTES", limit), \
                 patch.object(gate, "audit_single") as single, \
                 patch.object(gate, "audit_pair") as pair, \
                 patch.object(gate, "audit_marginals") as marginal, \
                 patch.object(gate, "audit_integer_feasibility") as integer:
                exit_code = gate.main(args)
            self.assertEqual(exit_code, 2)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "HOLD")
            self.assertIs(result["release_authorized"], False)
            self.assertIs(result["manual_review_required"], True)
            self.assertEqual(result["codes"], ["INPUT_READ_OR_PARSE_FAILED_CLOSED"])
            for screen in (single, pair, marginal, integer):
                screen.assert_not_called()
            self.assertEqual(files[source].read_bytes(), payload)
            self.assertNotIn("PRIVATE_SENTINEL", report.read_text(encoding="utf-8"))

    def test_oversized_candidate_fails_closed(self):
        self._hold_for_input("candidate", b'{"x":"' + b"PRIVATE_SENTINEL" * 6 + b'"}')

    def test_oversized_previous_fails_closed(self):
        self._hold_for_input("previous", b'{"x":"' + b"PRIVATE_SENTINEL" * 6 + b'"}')

    def test_oversized_marginal_evidence_fails_closed(self):
        self._hold_for_input("evidence", b'{"x":"' + b"PRIVATE_SENTINEL" * 6 + b'"}')

    def test_invalid_utf8_fails_closed(self):
        self._hold_for_input("candidate", b'{"x":"\xff"}')

    def test_exact_byte_limit_is_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "at-limit.json"
            payload = b'{"x":1}'
            source.write_bytes(payload)
            with patch.object(gate, "MAX_INPUT_BYTES", len(payload)):
                self.assertEqual(gate._read_strict_json(source), {"x": 1})

    def test_utf8_multibyte_character_counts_as_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "utf8.json"
            payload = '{"x":"é"}'.encode("utf-8")
            source.write_bytes(payload)
            with patch.object(gate, "MAX_INPUT_BYTES", len(payload) - 1):
                with self.assertRaises(ValueError):
                    gate._read_strict_json(source)
            with patch.object(gate, "MAX_INPUT_BYTES", len(payload)):
                self.assertEqual(gate._read_strict_json(source), {"x": "é"})

    def test_size_guard_precedes_utf8_decode(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "oversize-invalid.json"
            source.write_bytes(b"{" + b"\xff" * 100)
            with patch.object(gate, "MAX_INPUT_BYTES", 32):
                with self.assertRaisesRegex(ValueError, "oversized JSON input"):
                    gate._read_strict_json(source)


if __name__ == "__main__":
    unittest.main()
