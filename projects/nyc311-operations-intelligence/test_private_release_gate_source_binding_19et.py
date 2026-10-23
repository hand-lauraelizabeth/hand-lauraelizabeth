"""Synthetic, source-free regression tests for the private NYC 311 CSV byte-binding gate."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import private_release_gate as gate


class SourceCSVBindingTests(unittest.TestCase):
    SOURCE = b"synthetic,column\nfictional,example\n"

    def _run(self, *, source=None, digest=None, size=None, include_source=True):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            csv = root / "fictional.csv"
            candidate = root / "candidate.json"
            report = root / "report.json"
            csv.write_bytes(self.SOURCE if source is None else source)
            payload = {
                "source_sha256": hashlib.sha256(self.SOURCE).hexdigest()
                if digest is None else digest,
                "source_bytes": len(self.SOURCE) if size is None else size,
            }
            candidate.write_text(json.dumps(payload), encoding="utf-8")
            args = [str(candidate), "--report", str(report)]
            if include_source:
                args.extend(["--source-csv", str(csv)])
            with patch.object(gate, "audit_release", return_value={
                "status": "HOLD", "manual_review_required": True,
                "release_authorized": False, "codes": ["INDEPENDENT_REVIEW_REQUIRED"]
            }) as audit:
                self.assertEqual(gate.main(args), 2)
            audit.assert_called_once()
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "HOLD")
            self.assertIs(result["manual_review_required"], True)
            self.assertIs(result["release_authorized"], False)
            self.assertNotIn("fictional,example", report.read_text(encoding="utf-8"))
            self.assertEqual(csv.read_bytes(), self.SOURCE if source is None else source)
            return result["codes"]

    def test_matching_bytes_still_cannot_authenticate_origin(self):
        codes = self._run()
        self.assertIn("SOURCE_CSV_BYTES_MATCH_CANDIDATE_CLAIM", codes)
        self.assertIn("SOURCE_ORIGIN_NOT_AUTHENTICATED", codes)

    def test_same_length_mutation_is_detected(self):
        mutated = self.SOURCE.replace(b"fictional", b"ficti0nal")
        # Mutation above adds one byte; use an exact-length mutation instead.
        mutated = self.SOURCE.replace(b"fictional", b"fictionaL")
        self.assertEqual(len(mutated), len(self.SOURCE))
        self.assertIn("SOURCE_CSV_BINDING_FAILED", self._run(source=mutated))

    def test_size_mismatch_is_detected(self):
        self.assertIn("SOURCE_CSV_BINDING_FAILED",
                      self._run(size=len(self.SOURCE) + 1))

    def test_digest_mismatch_is_detected(self):
        self.assertIn("SOURCE_CSV_BINDING_FAILED", self._run(digest="0" * 64))

    def test_missing_csv_remains_explicitly_unverified(self):
        self.assertIn("SOURCE_CSV_NOT_SUPPLIED",
                      self._run(include_source=False))

    def test_boolean_source_size_is_not_accepted(self):
        self.assertIn("SOURCE_CSV_BINDING_FAILED", self._run(size=True))

    def test_missing_source_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / "candidate.json"
            report = root / "report.json"
            candidate.write_text(json.dumps({
                "source_sha256": hashlib.sha256(self.SOURCE).hexdigest(),
                "source_bytes": len(self.SOURCE)
            }), encoding="utf-8")
            with patch.object(gate, "audit_release", return_value={
                "status": "HOLD", "manual_review_required": True,
                "release_authorized": False, "codes": []
            }):
                self.assertEqual(gate.main([
                    str(candidate), "--source-csv", str(root / "absent.csv"),
                    "--report", str(report)
                ]), 2)
            codes = json.loads(report.read_text(encoding="utf-8"))["codes"]
            self.assertIn("SOURCE_CSV_READ_FAILED_CLOSED", codes)

    def test_report_alias_of_csv_is_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            csv = root / "fictional.csv"
            candidate = root / "candidate.json"
            csv.write_bytes(self.SOURCE)
            candidate.write_text("{}", encoding="utf-8")
            self.assertEqual(gate.main([
                str(candidate), "--source-csv", str(csv), "--report", str(csv)
            ]), 2)
            self.assertEqual(csv.read_bytes(), self.SOURCE)


if __name__ == "__main__":
    unittest.main()
