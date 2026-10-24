import unittest
from urllib.parse import urlencode
from source_export_query_contract import (check_export_query, query_fingerprint,
                                          DATASET, FIELDS, MONTH)


class QueryContractTests(unittest.TestCase):
    def make(self, **changes):
        params = {'$select': FIELDS, '$where': MONTH, '$order': 'unique_key ASC',
                  '$limit': '400000'}
        params.update(changes)
        return DATASET + '?' + urlencode(params)

    def test_valid_query_still_not_provenance(self):
        self.assertEqual(check_export_query(self.make(), reference_rows=323630),
                         ['SOURCE_QUERY_SHAPE_VERIFIED_NOT_PROVENANCE'])

    def test_url_fingerprint_is_deterministic(self):
        self.assertEqual(query_fingerprint(self.make()), query_fingerprint(self.make()))
        self.assertEqual(len(query_fingerprint(self.make())), 64)

    def test_bad_endpoint(self):
        self.assertEqual(check_export_query(self.make().replace('data.cityofnewyork.us',
                          'data.cityofnewyork.us.evil.example'), reference_rows=323630),
                         ['SOURCE_QUERY_ENDPOINT_INVALID'])

    def test_http_is_rejected(self):
        self.assertEqual(check_export_query(self.make().replace('https:', 'http:'),
                         reference_rows=323630), ['SOURCE_QUERY_ENDPOINT_INVALID'])

    def test_extra_parameter(self):
        self.assertEqual(check_export_query(self.make() + '&$offset=10',
                         reference_rows=323630), ['SOURCE_QUERY_PARAMETERS_INVALID'])

    def test_duplicate_parameter(self):
        self.assertEqual(check_export_query(self.make() + '&$limit=1',
                         reference_rows=323630), ['SOURCE_QUERY_PARAMETERS_INVALID'])

    def test_bad_date_scope(self):
        self.assertEqual(check_export_query(self.make(**{'$where': "created_date >= '2026-09-02'"}),
                         reference_rows=323630), ['SOURCE_QUERY_SCOPE_INVALID'])

    def test_missing_unique_key(self):
        self.assertEqual(check_export_query(self.make(**{'$select': 'created_date,borough'}),
                         reference_rows=323630), ['SOURCE_QUERY_SCOPE_INVALID'])

    def test_unstable_sort(self):
        self.assertEqual(check_export_query(self.make(**{'$order': 'created_date DESC'}),
                         reference_rows=323630), ['SOURCE_QUERY_SCOPE_INVALID'])

    def test_limit_equals_reference_is_rejected(self):
        self.assertEqual(check_export_query(self.make(**{'$limit': '323630'}),
                         reference_rows=323630), ['SOURCE_QUERY_LIMIT_INVALID'])

    def test_limit_over_budget(self):
        self.assertEqual(check_export_query(self.make(**{'$limit': '1000000000'}),
                         reference_rows=323630), ['SOURCE_QUERY_LIMIT_INVALID'])

    def test_bad_reference_count(self):
        self.assertEqual(check_export_query(self.make(), reference_rows=0),
                         ['SOURCE_QUERY_CONTRACT_INVALID'])

    def test_url_with_credentials(self):
        self.assertEqual(check_export_query(self.make().replace('https://', 'https://user:secret@'),
                         reference_rows=323630), ['SOURCE_QUERY_ENDPOINT_INVALID'])

    def test_url_with_fragment(self):
        self.assertEqual(check_export_query(self.make() + '#ignored', reference_rows=323630),
                         ['SOURCE_QUERY_ENDPOINT_INVALID'])

    def test_query_with_encoded_extra_secret(self):
        self.assertEqual(check_export_query(self.make() + '&%24%24app_token=secret',
                         reference_rows=323630), ['SOURCE_QUERY_PARAMETERS_INVALID'])


if __name__ == '__main__':
    unittest.main()
