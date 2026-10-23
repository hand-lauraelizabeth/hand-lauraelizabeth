"""Adversarial synthetic-only tests for conservative disclosure gate."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import release_disclosure_audit as gate


def fixture(*, cells=(12, 2), closures=(0, 0), minimum=10):
    visible = []
    for i, (n, c) in enumerate(zip(cells, closures)):
        if n >= minimum:
            visible.append({'month':'2026-09','borough':'QUEENS','agency':'Fictional',
                            'problem':f'Case-{i}','requests':n,'closed_with_valid_interval':c})
    return {'source':gate.SOURCE,'dataset_id':'erm2-nwe9','source_sha256':'a'*64,
            'source_bytes':300,'snapshot_as_of':'2026-09-30',
            'rules':{'display_minimum_cell_count':minimum,
                     'grain':'month × borough × agency × original API complaint_type'},
            'quality':{'rows_read':sum(cells),'unique_keys_verified':sum(cells),
                       'valid_records':sum(cells),
                       'small_cells_suppressed':sum(1 for n in cells if n < minimum)},
            'aggregates':visible}


class DisclosureAuditTests(unittest.TestCase):
    def test_single_suppressed_cell_reconstructed(self):
        result = gate.audit_single(fixture())
        self.assertTrue(result['structural_valid'])
        self.assertIn('SUPPRESSED_CELL_EXACTLY_RECONSTRUCTIBLE', result['codes'])
        self.assertNotIn('Case-0', json.dumps(result))
        self.assertNotIn('"2"', json.dumps(result))

    def test_multiple_suppressed_cells_residual_still_unsafe(self):
        result = gate.audit_single(fixture(cells=(20, 3, 4), closures=(0, 0, 0)))
        self.assertIn('SUPPRESSED_RESIDUAL_EXPOSED_BY_TOTAL', result['codes'])
        self.assertNotIn('SUPPRESSED_CELL_EXACTLY_RECONSTRUCTIBLE', result['codes'])

    def test_small_closure_and_complement(self):
        for c in (2, 18):
            with self.subTest(c=c):
                result = gate.audit_single(fixture(cells=(20,), closures=(c,)))
                self.assertIn('SMALL_CLOSURE_OR_COMPLEMENT_EXPOSED', result['codes'])

    def test_small_quality_counter(self):
        data = fixture(cells=(20,), closures=(0,))
        data['quality']['missing_agency'] = 1
        self.assertIn('SMALL_QUALITY_COUNTER_EXPOSED', gate.audit_single(data)['codes'])

    def test_tampered_duplicate_cell_and_residual(self):
        data = fixture(cells=(20,), closures=(0,))
        data['aggregates'].append(dict(data['aggregates'][0]))
        self.assertFalse(gate.audit_single(data)['structural_valid'])
        data = fixture()
        data['quality']['valid_records'] = 100
        self.assertFalse(gate.audit_single(data)['structural_valid'])

    def test_small_temporal_differences(self):
        a = fixture(cells=(20,), closures=(10,))
        b = fixture(cells=(21,), closures=(11,))
        result = gate.audit_pair(a, b)
        self.assertIn('SMALL_REQUEST_DELTA_EXPOSED', result['codes'])
        self.assertIn('SMALL_CLOSURE_DELTA_EXPOSED', result['codes'])
        self.assertIn('SMALL_COHORT_TOTAL_DELTA_EXPOSED', result['codes'])

    def test_visibility_change(self):
        a = fixture(cells=(12, 2), closures=(0, 0))
        b = fixture(cells=(12, 10), closures=(0, 0))
        self.assertIn('DISPLAY_CELL_SET_CHANGED', gate.audit_pair(a, b)['codes'])

    def test_cli_fails_closed_with_redacted_report(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td)/'candidate.json'
            report = Path(td)/'report.json'
            source.write_text(json.dumps(fixture()))
            with patch('sys.argv', ['gate', str(source), '--report', str(report)]):
                with self.assertRaises(SystemExit) as ctx:
                    gate.main()
            self.assertEqual(ctx.exception.code, 2)
            data = report.read_text()
            self.assertIn('HOLD', data)
            self.assertNotIn('Case-0', data)

    def test_not_authorized_even_without_obvious_small_cells(self):
        result = gate.audit_single(fixture(cells=(20,), closures=(0,)))
        self.assertEqual(result['status'], 'HOLD')
        self.assertIn('CROSS_TABLE_EXTERNAL_SOURCE_REVIEW_REQUIRED', result['codes'])


if __name__ == '__main__': unittest.main()
