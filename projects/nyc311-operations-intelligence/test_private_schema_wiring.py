"""Synthetic schema validation for private aggregate payloads."""
import unittest
from privacy_schema import assert_approved_payload_fields


class PrivateSchemaTests(unittest.TestCase):
    def test_valid_aggregate(self):
        payload = {'rules': {'display_minimum_cell_count': 10}, 'aggregates': [
            {'month': '2026-09', 'borough': 'QUEENS', 'agency': 'DOT',
             'problem': 'Pothole', 'requests': 20,
             'closed_with_valid_interval': None, 'closure_count_suppressed': True}]}
        assert_approved_payload_fields(payload)

    def test_unknown_detail_field_rejected(self):
        payload = {'rules': {}, 'aggregates': [{'month': '2026-09', 'unexpected': 'synthetic'}]}
        with self.assertRaises(ValueError):
            assert_approved_payload_fields(payload)


if __name__ == '__main__':
    unittest.main()
