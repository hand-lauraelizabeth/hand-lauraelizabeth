"""Offline checks for schema-before-rows acquisition and provenance sidecar."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from verified_source_export import acquire_verified
from source_schema import validate_schema, REQUIRED_TYPES


def evidence():
    return validate_schema({'id': 'erm2-nwe9', 'columns': [
        {'fieldName': k, 'dataTypeName': v} for k, v in REQUIRED_TYPES.items()]})


class VerifiedExportTests(unittest.TestCase):
    def test_schema_precedes_export_and_proof_persists(self):
        order = []
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / '2026-09.csv'
            def schema():
                order.append('schema')
                return evidence()
            def export(month, path, **kwargs):
                order.append('export')
                self.assertEqual(month, '2026-09')
                self.assertEqual(kwargs['expected_count'], 2)
                Path(path).write_text('synthetic\n')
                return {'rows_exported': 2, 'sha256': 'a' * 64}
            with patch('verified_source_export.fetch_schema', side_effect=schema), patch('verified_source_export.acquire', side_effect=export):
                result, proof = acquire_verified('2026-09', output, expected_count=2)
            self.assertEqual(order, ['schema', 'export'])
            self.assertEqual(result['rows_exported'], 2)
            self.assertEqual(json.loads(Path(str(output) + '.schema.json').read_text()), proof)

    def test_metadata_failure_blocks_records_and_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / '2026-09.csv'
            with patch('verified_source_export.fetch_schema', side_effect=ValueError('schema drift')):
                with patch('verified_source_export.acquire') as export:
                    with self.assertRaisesRegex(ValueError, 'schema drift'):
                        acquire_verified('2026-09', output)
                    export.assert_not_called()
            self.assertFalse(output.exists())
            self.assertFalse(Path(str(output) + '.schema.json').exists())

    def test_export_failure_does_not_write_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / '2026-09.csv'
            with patch('verified_source_export.fetch_schema', return_value=evidence()):
                with patch('verified_source_export.acquire', side_effect=ValueError('count changed')):
                    with self.assertRaisesRegex(ValueError, 'count changed'):
                        acquire_verified('2026-09', output)
            self.assertFalse(Path(str(output) + '.schema.json').exists())

    def test_existing_proof_prevents_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / '2026-09.csv'
            Path(str(output) + '.schema.json').write_text('previous')
            with patch('verified_source_export.fetch_schema') as schema:
                with self.assertRaises(FileExistsError):
                    acquire_verified('2026-09', output)
                schema.assert_not_called()


if __name__ == '__main__': unittest.main()
