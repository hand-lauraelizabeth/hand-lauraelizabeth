"""Synthetic-only regression cases for exact-rational cross-table inference."""
import json
import unittest
import marginal_reconstruction_audit as gate


class MarginalReconstructionTests(unittest.TestCase):
    def setUp(self):
        # Two rows and two columns of fictional aggregate cells.
        self.matrix = [[1, 1, 0, 0], [0, 0, 1, 1],
                       [1, 0, 1, 0], [0, 1, 0, 1]]
        self.totals = [30, 30, 20, 40]

    def test_marginals_alone_do_not_uniquely_identify_a_cell(self):
        r = gate.audit_marginals(self.matrix, self.totals, [0])
        self.assertTrue(r['structural_valid'])
        self.assertIn('UNDERDETERMINED_LINEAR_SYSTEM', r['codes'])
        self.assertNotIn('SUPPRESSED_VARIABLE_RECONSTRUCTIBLE_FROM_MARGINALS', r['codes'])

    def test_additional_published_cell_reconstructs_suppressed(self):
        r = gate.audit_marginals(self.matrix + [[0, 1, 0, 0]],
                                 self.totals + [20], [0])
        self.assertIn('SUPPRESSED_VARIABLE_RECONSTRUCTIBLE_FROM_MARGINALS', r['codes'])
        self.assertEqual(r['status'], 'HOLD')
        self.assertNotIn('"10"', json.dumps(r))
        self.assertNotIn('"20"', json.dumps(r))

    def test_redundant_marginal_does_not_create_false_uniqueness(self):
        r = gate.audit_marginals(self.matrix + [self.matrix[0]],
                                 self.totals + [self.totals[0]], [0])
        self.assertNotIn('SUPPRESSED_VARIABLE_RECONSTRUCTIBLE_FROM_MARGINALS', r['codes'])

    def test_inconsistent_marginals_fail_closed(self):
        r = gate.audit_marginals(self.matrix + [self.matrix[0]],
                                 self.totals + [31], [0])
        self.assertFalse(r['structural_valid'])
        self.assertIn('INCONSISTENT_PUBLIC_MARGINALS', r['codes'])

    def test_directly_published_suppressed_cell_detected(self):
        r = gate.audit_marginals([[1, 0]], [12], [0])
        self.assertIn('SUPPRESSED_VARIABLE_RECONSTRUCTIBLE_FROM_MARGINALS', r['codes'])

    def test_non_suppressed_unique_variable_not_false_positive(self):
        r = gate.audit_marginals([[1, 0]], [12], [1])
        self.assertNotIn('SUPPRESSED_VARIABLE_RECONSTRUCTIBLE_FROM_MARGINALS', r['codes'])

    def test_invalid_dimensions_and_boolean_coefficients(self):
        for mat, totals, hidden in [([[1, 0]], [], [0]),
                                    ([[True, 0]], [1], [0]),
                                    ([[1, 0]], [1], [2]),
                                    ([[1, 0]], [1], [0, 0]),
                                    ([[1, -1]], [1], [0]),
                                    ([[1, 0]], [-1], [0])]:
            with self.subTest(mat=mat, totals=totals, hidden=hidden):
                r = gate.audit_marginals(mat, totals, hidden)
                self.assertFalse(r['structural_valid'])
                self.assertEqual(r['status'], 'HOLD')

    def test_no_hidden_variable_does_not_grant_release(self):
        r = gate.audit_marginals([[1, 1]], [20], [])
        self.assertEqual(r['status'], 'HOLD')
        self.assertIn('INTEGER_BOUND_EXTERNAL_AND_TEMPORAL_REVIEW_REQUIRED', r['codes'])

    def test_fractional_solution_still_not_release_approval(self):
        r = gate.audit_marginals([[2, 0], [0, 2]], [3, 5], [0])
        self.assertTrue(r['structural_valid'])
        self.assertEqual(r['status'], 'HOLD')
        self.assertIn('INTEGER_BOUND_EXTERNAL_AND_TEMPORAL_REVIEW_REQUIRED', r['codes'])


if __name__ == '__main__':
    unittest.main()
