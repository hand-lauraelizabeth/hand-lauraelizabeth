"""Synthetic-only integer/nonnegative inference regression tests."""
import json
import unittest
from integer_feasibility_audit import audit_integer_feasibility as audit

class IntegerFeasibilityTests(unittest.TestCase):
    def test_integer_fixed_but_linear_underdetermined(self):
        # 2*x+3*y=3 has infinitely many real, one nonnegative integer solution.
        result = audit([[2, 3]], [3], [0, 1], [[0, 1]])
        self.assertIn('SUPPRESSED_VARIABLE_INTEGER_RECONSTRUCTIBLE', result['codes'])
        self.assertIn('SENSITIVE_GROUP_SUM_INTEGER_RECONSTRUCTIBLE', result['codes'])
        self.assertEqual(result['status'], 'HOLD')

    def test_ambiguous_individuals_with_fixed_group(self):
        result = audit([[1, 1]], [3], [0, 1], [[0, 1]])
        self.assertNotIn('SUPPRESSED_VARIABLE_INTEGER_RECONSTRUCTIBLE', result['codes'])
        self.assertIn('SENSITIVE_GROUP_SUM_INTEGER_RECONSTRUCTIBLE', result['codes'])

    def test_ambiguous_individual_and_group(self):
        result = audit([[1, 1, 1]], [2], [0, 1], [[0, 1]])
        self.assertNotIn('SUPPRESSED_VARIABLE_INTEGER_RECONSTRUCTIBLE', result['codes'])
        self.assertNotIn('SENSITIVE_GROUP_SUM_INTEGER_RECONSTRUCTIBLE', result['codes'])

    def test_zero_total_fixes_everything(self):
        self.assertIn('SUPPRESSED_VARIABLE_INTEGER_RECONSTRUCTIBLE',
                      audit([[1, 1]], [0], [0, 1])['codes'])

    def test_no_feasible_integer_solution(self):
        self.assertEqual(audit([[2]], [1], [0])['codes'],
                         ['NO_FEASIBLE_INTEGER_ASSIGNMENT'])

    def test_unbounded_variable(self):
        self.assertEqual(audit([[1, 0]], [2], [0, 1])['codes'],
                         ['UNBOUNDED_INTEGER_VARIABLE'])

    def test_budget_exceeded_fails_closed(self):
        self.assertEqual(audit([[1] * 8], [200], [0])['codes'],
                         ['INTEGER_AUDIT_BUDGET_EXCEEDED'])

    def test_large_dimensions_scope_exceeded(self):
        self.assertEqual(audit([[1] * 9], [1], [0])['codes'],
                         ['INTEGER_AUDIT_SCOPE_EXCEEDED'])

    def test_malformed_input_fails_closed(self):
        for matrix, totals, suppressed, groups in [
            ([[True]], [1], [0], []), ([[1]], [-1], [0], []),
            ([[1]], [1], [True], []), ([[1]], [1], [0, 0], []),
            ([[1]], [1], [0], [[0, 0]]), ([[1]], [1], [0], [[1]]),
            ([[1]], [1], [0], '0'), ([[1, 2], [1]], [1, 1], [0], []),
        ]:
            with self.subTest(matrix=matrix, groups=groups):
                self.assertEqual(audit(matrix, totals, suppressed, groups)['codes'],
                                 ['INVALID_INTEGER_CONTRACT'])

    def test_redacted_schema_and_no_values(self):
        result = audit([[2, 3]], [3], [0, 1], [[0, 1]])
        self.assertEqual(set(result), {'status', 'manual_review_required', 'codes'})
        self.assertTrue(result['manual_review_required'])
        self.assertNotIn('"3"', json.dumps(result))
        self.assertNotIn('[[0, 1]]', json.dumps(result))

if __name__ == '__main__':
    unittest.main()
