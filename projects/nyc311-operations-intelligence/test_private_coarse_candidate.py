"""Fabricated-only regression for private NYC 311 coarsening candidate."""
import unittest
from private_coarse_candidate import build_candidate


def candidate(src, closures, *, as_of, min_cell=10):
    return build_candidate(src, closures, as_of=as_of, min_cell=min_cell,
                           expected_valid_records=sum(src.values()))


class CoarseCandidateTests(unittest.TestCase):
    def test_combine_before_suppress_without_exact_quality_marginals(self):
        a = ("2026-09", "QUEENS", "DOT", "Synthetic Visible")
        b = ("2026-09", "QUEENS", "DOT", "Synthetic Withheld")
        result = candidate({a: 12, b: 3}, {}, as_of="2026-10-25")
        self.assertEqual(len(result["aggregates"]), 1)
        self.assertEqual(result["aggregates"][0]["requests"], 15)
        self.assertEqual(result["aggregates"][0]["closed_with_valid_interval"], 0)
        raw = repr(result)
        for secret in ("Synthetic Visible", "Synthetic Withheld", "valid_records",
                       "small_cells_suppressed", "rows_read", "source_sha256",
                       "source_bytes", "unique_key"):
            self.assertNotIn(secret, raw)
        self.assertFalse(result["publication_approved"])
        self.assertEqual(result["rules"]["grain"], ["month", "borough", "agency"])

    def test_threshold_and_closure_complement_suppression(self):
        a = ("2026-09", "BRONX", "DOT", "Fixture")
        self.assertEqual(candidate({a: 9}, {}, as_of="2026-10-25")["aggregates"], [])
        for closed in (1, 9, 11, 19):
            result = candidate({a: 20}, {a: closed}, as_of="2026-10-25")
            self.assertIsNone(result["aggregates"][0]["closed_with_valid_interval"])
        for closed in (0, 10, 20):
            result = candidate({a: 20}, {a: closed}, as_of="2026-10-25")
            self.assertEqual(result["aggregates"][0]["closed_with_valid_interval"], closed)

    def test_multiple_agencies_are_separate(self):
        a = ("2026-09", "QUEENS", "DOT", "Fixture")
        b = ("2026-09", "QUEENS", "DEP", "Fixture")
        rows = candidate({a: 12, b: 11}, {}, as_of="2026-10-25")["aggregates"]
        self.assertEqual([(r["agency"], r["requests"]) for r in rows],
                         [("DEP", 11), ("DOT", 12)])

    def test_rejects_partial_post_suppression_counts_and_invalid_inputs(self):
        a = ("2026-09", "QUEENS", "DOT", "Fixture")
        bad = [
            ({}, {}, "2026-10-25", 10),
            ({a: True}, {}, "2026-10-25", 10),
            ({a: -1}, {}, "2026-10-25", 10),
            ({a: 10}, {a: 11}, "2026-10-25", 10),
            ({a: 10}, {("2026-09", "QUEENS", "DOT", "Other"): 1}, "2026-10-25", 10),
            ({a: 10}, {}, "2026-08-25", 10),
            ({a: 10}, {}, "2026-10-25", 1),
            ({a: 10}, {}, "2026-10-25", True),
            ({a: 10}, {}, "2026-13-25", 10),
        ]
        for src, closures, as_of, k in bad:
            with self.subTest(as_of=as_of, min_cell=k):
                with self.assertRaises(ValueError):
                    candidate(src, closures, as_of=as_of, min_cell=k)

    def test_fails_closed_on_incomplete_source_groups(self):
        a = ("2026-09", "QUEENS", "DOT", "Fixture")
        with self.assertRaisesRegex(ValueError, "Incomplete source-group"):
            build_candidate({a: 12}, {}, as_of="2026-10-25",
                            expected_valid_records=15)

    def test_does_not_mutate_private_counters(self):
        a = ("2026-09", "QUEENS", "DOT", "Fixture")
        src, closed = {a: 18}, {a: 14}
        before = (dict(src), dict(closed))
        candidate(src, closed, as_of="2026-10-25")
        self.assertEqual((src, closed), before)


if __name__ == "__main__":
    unittest.main()
