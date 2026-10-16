"""Deterministic disclosure-gate tests; fabricated records only."""
import unittest
from disclosure import publish_cells

def cell(problem, requests, closed=None):
    d = dict(month="2026-09", borough="QUEENS", agency="DOT", problem=problem, requests=requests)
    if closed is not None:
        d["closed_with_valid_interval"] = closed
    return d

class DisclosureTests(unittest.TestCase):
    def test_suppressed_counts_not_reconstructable_from_totals(self):
        result = publish_cells([cell("a", 2), cell("b", 10), cell("c", 17)], minimum=10)
        self.assertEqual([x["requests"] for x in result["cells"]], [10, 17])
        self.assertFalse(result["marginals_available"])
        self.assertNotIn("source_total", result)
        self.assertNotIn("suppressed_total", result)

    def test_closure_partition_suppressed(self):
        result = publish_cells([cell("a", 20, 19), cell("b", 22, 11)])
        self.assertNotIn("closed_with_valid_interval", result["cells"][0])
        self.assertEqual(result["cells"][1]["closed_with_valid_interval"], 11)

    def test_reject_duplicate_and_invalid(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            publish_cells([cell("a", 10), cell("a", 10)])
        with self.assertRaisesRegex(ValueError, "invalid closed"):
            publish_cells([cell("a", 10, 11)])
        with self.assertRaises(ValueError):
            publish_cells([cell("a", 10)], minimum=1)

if __name__ == "__main__":
    unittest.main()
