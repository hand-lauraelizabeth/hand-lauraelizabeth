"""Synthetic regression: disclosure of sums across individually suppressed cells.

This tests a *necessary-only* exact-rational screen, not privacy certification.
No operational NYC 311 records, suppressed values, or identifiers are included.
"""
import json
import unittest
import marginal_reconstruction_audit as audit


class SensitiveGroupMarginalTests(unittest.TestCase):
    def setUp(self):
        # Synthetic 2x2 table with row and column totals; rank 3, nullity 1.
        self.rows = [[1, 1, 0, 0], [0, 0, 1, 1],
                     [1, 0, 1, 0], [0, 1, 0, 1]]
        self.totals = [30, 30, 20, 40]

    def test_two_individually_unknown_cells_have_known_sum(self):
        result = audit.audit_marginals(
            self.rows, self.totals, [0, 1], sensitive_groups=[[0, 1]])
        self.assertTrue(result['structural_valid'])
        self.assertIn('UNDERDETERMINED_LINEAR_SYSTEM', result['codes'])
        self.assertNotIn('SUPPRESSED_VARIABLE_RECONSTRUCTIBLE_FROM_MARGINALS',
                         result['codes'])
        self.assertIn('SENSITIVE_GROUP_SUM_RECONSTRUCTIBLE_FROM_MARGINALS',
                      result['codes'])
        self.assertEqual(result['status'], 'HOLD')

    def test_diagonal_sum_not_linearly_identifiable(self):
        result = audit.audit_marginals(
            self.rows, self.totals, [0, 3], sensitive_groups=[[0, 3]])
        self.assertNotIn('SENSITIVE_GROUP_SUM_RECONSTRUCTIBLE_FROM_MARGINALS',
                         result['codes'])
        self.assertEqual(result['status'], 'HOLD')

    def test_multiple_groups_any_identifiable_triggers_warning(self):
        result = audit.audit_marginals(
            self.rows, self.totals, [0, 1, 3],
            sensitive_groups=[[0, 3], [0, 1]])
        self.assertIn('SENSITIVE_GROUP_SUM_RECONSTRUCTIBLE_FROM_MARGINALS',
                      result['codes'])

    def test_redundant_constraint_does_not_invent_group_uniqueness(self):
        result = audit.audit_marginals(
            self.rows + [self.rows[0]], self.totals + [30],
            [0, 3], sensitive_groups=[[0, 3]])
        self.assertNotIn('SENSITIVE_GROUP_SUM_RECONSTRUCTIBLE_FROM_MARGINALS',
                         result['codes'])

    def test_invalid_group_contracts_fail_closed(self):
        invalid = [
            '0,1', [[0, 0]], [[0, 2]], [[True]], [[]],
            [[4]], [[0, 1, 1]], [[0], []], [None], [[0.0]],
        ]
        for groups in invalid:
            with self.subTest(groups=groups):
                result = audit.audit_marginals(
                    self.rows, self.totals, [0, 1], sensitive_groups=groups)
                self.assertFalse(result['structural_valid'])
                self.assertEqual(result['status'], 'HOLD')
                self.assertIn('INVALID_MARGINAL_CONTRACT', result['codes'])

    def test_inconsistent_totals_remain_fail_closed(self):
        result = audit.audit_marginals(
            self.rows + [self.rows[0]], self.totals + [31],
            [0, 1], sensitive_groups=[[0, 1]])
        self.assertFalse(result['structural_valid'])
        self.assertIn('INCONSISTENT_PUBLIC_MARGINALS', result['codes'])

    def test_no_group_preserves_legacy_contract(self):
        old = audit.audit_marginals(self.rows, self.totals, [0, 1])
        explicit = audit.audit_marginals(
            self.rows, self.totals, [0, 1], sensitive_groups=[])
        self.assertEqual(old, explicit)
        self.assertNotIn('SENSITIVE_GROUP_SUM_RECONSTRUCTIBLE_FROM_MARGINALS',
                         old['codes'])

    def test_no_indices_totals_or_reconstructed_values_emitted(self):
        result = audit.audit_marginals(
            self.rows, self.totals, [0, 1], sensitive_groups=[[0, 1]])
        self.assertEqual(set(result),
                         {'status', 'structural_valid', 'codes',
                          'manual_review_required'})
        self.assertTrue(all(isinstance(code, str) for code in result['codes']))
        serialized = json.dumps(result)
        self.assertNotIn('"30"', serialized)
        self.assertNotIn('"20"', serialized)
        self.assertNotIn('[[0, 1]]', serialized)

    def test_independent_integer_enumeration_confirms_hidden_pair_ambiguity(self):
        # Independent finite oracle: feasible integer cells, not a second
        # implementation of the rank algorithm.
        candidates = []
        for a in range(21):
            b, c, d = 30 - a, 20 - a, 10 + a
            if min(a, b, c, d) >= 0 and b + d == 40:
                candidates.append((a, b, c, d))
        self.assertEqual(len(candidates), 21)
        self.assertGreater(len({v[0] for v in candidates}), 1)
        self.assertEqual({v[0] + v[1] for v in candidates}, {30})
        self.assertGreater(len({v[0] + v[3] for v in candidates}), 1)


if __name__ == '__main__':
    unittest.main()
