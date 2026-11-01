"""Deterministic contract checks; these are fixture tests, not live-source processing."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from pipeline import ingest

FIELDS = ["unique_key","created_date","closed_date","agency","complaint_type","borough","status"]

class TestPipeline(unittest.TestCase):
    def test_aggregations_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp, out = Path(tmp)/"fixture.csv", Path(tmp)/"result.json"
            rows = [
                ["1","2026-01-10T09:00:00.000","2026-01-11T09:00:00.000","DOT","Pothole","Queens","Closed"],
                ["2","2026-01-10T09:00:00.000","","DOT","Pothole","Queens","Open"],
                ["3","2026-02-10T09:00:00.000","2026-02-09T09:00:00.000","DOT","Pothole","Queens","Closed"],
                ["4","nonsense","","DOT","Pothole","Queens","Open"],
                ["5","2026-11-01T09:00:00.000","","DOT","Pothole","Queens","Open"],
                ["6","2026-01-10T09:00:00.000","","","Noise","","Open"],
            ]
            with inp.open("w",newline="",encoding="utf-8") as f:
                w = csv.writer(f); w.writerow(FIELDS); w.writerows(rows)
            obj = ingest(inp,out,as_of="2026-10-15",min_cell=2)
            self.assertEqual(obj["quality"]["rows_read"],6)
            self.assertEqual(obj["quality"]["valid_records"],4)
            self.assertEqual(obj["quality"]["missing_or_invalid_created_date"],1)
            self.assertEqual(obj["quality"]["created_after_as_of"],1)
            self.assertEqual(obj["quality"]["closure_before_creation"],1)
            self.assertEqual(obj["quality"]["small_cells_suppressed"],2)
            self.assertEqual(obj["aggregates"][0]["requests"],2)
            self.assertIsNone(obj["aggregates"][0]["closed_with_valid_interval"])
            self.assertEqual(obj["quality"]["closure_subcells_suppressed"], 1)
            self.assertNotIn("incident_address",out.read_text())
            self.assertEqual(json.loads(out.read_text())["source_sha256"],obj["source_sha256"])
    def test_closed_date_on_nonclosed_status_never_counts_as_closed(self):
        # Public-source QA found that a closed_date can coexist with an
        # administratively non-Closed status. Synthetic records only.
        with tempfile.TemporaryDirectory() as tmp:
            inp, out = Path(tmp)/"status_fixture.csv", Path(tmp)/"result.json"
            rows = [
                [str(i), "2026-09-10T09:00:00.000",
                 "2026-09-11T09:00:00.000", "DOT", "Pothole", "Queens", status]
                for i, status in enumerate(
                    ["Assigned", "In Progress", "Open", "Pending", "Unspecified"],
                    start=1)
            ]
            rows.extend([
                ["6", "2026-09-10T09:00:00.000",
                 "2026-09-11T09:00:00.000", "DOT", "Pothole", "Queens", "Closed"],
                ["7", "2026-09-10T09:00:00.000",
                 "", "DOT", "Pothole", "Queens", "Closed"],
            ])
            with inp.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(FIELDS)
                writer.writerows(rows)
            result = ingest(inp, out, as_of="2026-10-25", min_cell=1)
            self.assertEqual(result["quality"]["rows_read"], 7)
            self.assertEqual(result["quality"]["valid_records"], 7)
            self.assertEqual(len(result["aggregates"]), 1)
            self.assertEqual(result["aggregates"][0]["requests"], 7)
            self.assertEqual(result["aggregates"][0]["closed_with_valid_interval"], 1)

    def test_closed_status_requires_valid_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp, out = Path(tmp)/"interval_fixture.csv", Path(tmp)/"result.json"
            rows = [
                ["1", "2026-09-10T09:00:00.000",
                 "2026-09-09T09:00:00.000", "DOT", "Pothole", "Queens", "Closed"],
                ["2", "2026-09-10T09:00:00.000",
                 "2026-10-26T09:00:00.000", "DOT", "Pothole", "Queens", "Closed"],
                ["3", "2026-09-10T09:00:00.000",
                 "2026-09-11T09:00:00.000", "DOT", "Pothole", "Queens", "Closed"],
                ["4", "2026-09-10T09:00:00.000",
                 "", "DOT", "Pothole", "Queens", "Closed"],
            ]
            with inp.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(FIELDS)
                writer.writerows(rows)
            result = ingest(inp, out, as_of="2026-10-25", min_cell=1)
            self.assertEqual(result["quality"]["rows_read"], 4)
            self.assertEqual(result["quality"]["closure_before_creation"], 1)
            self.assertEqual(result["quality"]["closure_after_as_of"], 1)
            self.assertEqual(result["aggregates"][0]["requests"], 4)
            self.assertEqual(result["aggregates"][0]["closed_with_valid_interval"], 1)

    def test_required_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp, out = Path(tmp)/"invalid.csv", Path(tmp)/"result.json"
            inp.write_text("unique_key,created_date\n1,2026-01-01\n")
            with self.assertRaisesRegex(ValueError,"Missing API columns"):
                ingest(inp,out,as_of="2026-10-15")
            self.assertFalse(out.exists())
class TestInputOutputIsolation(unittest.TestCase):
    def test_source_is_not_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.csv"
            source.write_text(",".join(FIELDS) + "\n1,2026-09-01T10:00:00,,DOT,Pothole,Queens,Open\n")
            original = source.read_bytes()
            with self.assertRaisesRegex(ValueError, "distinct files"):
                ingest(source, source, as_of="2026-09-30")
            self.assertEqual(source.read_bytes(), original)

    def test_separate_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source.csv", Path(tmp) / "output.json"
            source.write_text(",".join(FIELDS) + "\n1,2026-09-01T10:00:00,,DOT,Pothole,Queens,Open\n")
            result = ingest(source, output, as_of="2026-09-30")
            self.assertEqual(result["quality"]["rows_read"], 1)
            self.assertTrue(output.exists())


class TestClosureSubcellPrivacy(unittest.TestCase):
    def test_closure_and_complement_thresholds_are_fail_closed(self):
        # All records are synthetic. A large denominator can hide a small
        # closure numerator OR a small still-open complement.
        with tempfile.TemporaryDirectory() as tmp:
            inp, out = Path(tmp)/"subcell.csv", Path(tmp)/"public.json"
            cases = [0, 1, 4, 5, 6, 7, 8, 11, 12]
            with inp.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(FIELDS)
                key = 0
                for closed_count in cases:
                    for position in range(12):
                        key += 1
                        is_closed = position < closed_count
                        writer.writerow([
                            str(key), "2026-09-10T09:00:00.000",
                            "2026-09-11T09:00:00.000" if is_closed else "",
                            "DOT", f"Synthetic type {closed_count:02d}",
                            "Queens", "Closed" if is_closed else "Open"
                        ])
                # A separate small request group must never appear at all.
                for _ in range(4):
                    key += 1
                    writer.writerow([
                        str(key), "2026-09-10T09:00:00.000",
                        "2026-09-11T09:00:00.000", "DOT",
                        "Synthetic small group", "Queens", "Closed"
                    ])
            result = ingest(inp, out, as_of="2026-10-25", min_cell=5)
            self.assertEqual(result["quality"]["rows_read"], 112)
            self.assertEqual(result["quality"]["small_cells_suppressed"], 1)
            self.assertEqual(result["quality"]["closure_subcells_suppressed"], 4)
            self.assertEqual(len(result["aggregates"]), 9)
            actual = {int(row["problem"].rsplit(" ", 1)[-1]):
                      row["closed_with_valid_interval"]
                      for row in result["aggregates"]}
            expected = {0: 0, 1: None, 4: None, 5: 5, 6: 6,
                        7: 7, 8: None, 11: None, 12: 12}
            self.assertEqual(actual, expected)
            published = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(published["aggregates"], result["aggregates"])
            self.assertNotIn("Synthetic small group", out.read_text())
            self.assertIsNone(actual[11])
            self.assertIsNone(actual[1])

    def test_single_record_threshold_allows_counts_without_false_nulls(self):
        # With min_cell=1 no positive subcell is below the threshold.
        with tempfile.TemporaryDirectory() as tmp:
            inp, out = Path(tmp)/"single.csv", Path(tmp)/"public.json"
            with inp.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(FIELDS)
                writer.writerow(["1", "2026-09-10T09:00:00.000",
                                 "2026-09-11T09:00:00.000",
                                 "DOT", "Synthetic", "Queens", "Closed"])
            result = ingest(inp, out, as_of="2026-10-25", min_cell=1)
            self.assertEqual(result["aggregates"][0]["closed_with_valid_interval"], 1)
            self.assertEqual(result["quality"].get("closure_subcells_suppressed", 0), 0)


class TestStrictReportingMonthClosure(unittest.TestCase):
    """Synthetic CSV fixtures: a full-month claim requires next-day dating."""

    def _case(self, month, last_day, first_after):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.csv"
            output = Path(tmp) / "output.json"
            with source.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(FIELDS)
                writer.writerow(["fixture-1", month + "-10T12:00:00.000",
                                 "", "DOT", "Synthetic", "Queens", "Open"])
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            output.write_text("preserve existing output", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Snapshot precedes completion"):
                ingest(source, output, as_of=last_day, reporting_month=month,
                       expected_sha256=sha, expected_rows=1, min_cell=1)
            self.assertEqual(output.read_text(encoding="utf-8"),
                             "preserve existing output")
            result = ingest(source, output, as_of=first_after,
                            reporting_month=month, expected_sha256=sha,
                            expected_rows=1, min_cell=1)
            self.assertEqual(result["quality"]["reporting_month_rows_verified"], 1)
            self.assertEqual(result["quality"]["unique_keys_verified"], 1)
            self.assertEqual(result["rules"]["strict_reporting_month"], month)
            self.assertTrue(result["quality"]["supplied_manifest_verified"])

    def test_september_last_day_rejected_october_first_accepted(self):
        self._case("2026-09", "2026-09-30", "2026-10-01")

    def test_december_rollover_requires_january_first(self):
        self._case("2026-12", "2026-12-31", "2027-01-01")

    def test_leap_february_requires_march_first(self):
        self._case("2028-02", "2028-02-29", "2028-03-01")

    def test_non_strict_partial_month_ingest_does_not_claim_full_month(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source.csv", Path(tmp) / "output.json"
            with source.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(FIELDS)
                writer.writerow(["fixture-1", "2026-09-10T12:00:00.000",
                                 "", "DOT", "Synthetic", "Queens", "Open"])
            result = ingest(source, output, as_of="2026-09-30", min_cell=1)
            self.assertEqual(result["quality"]["rows_read"], 1)
            self.assertNotIn("strict_reporting_month", result["rules"])

class TestStrictMalformedClosureDate(unittest.TestCase):
    """Synthetic fixtures: invalid nonempty closure dates must fail closed."""

    def test_strict_cohort_rejects_malformed_nonempty_closure(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source.csv", Path(tmp) / "output.json"
            with source.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(FIELDS)
                writer.writerow(["fixture-1", "2026-09-10T09:00:00.000",
                                 "not-a-timestamp", "DOT", "Synthetic",
                                 "Queens", "Closed"])
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            output.write_text("preserve original", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid closed_date"):
                ingest(source, output, as_of="2026-10-25",
                       reporting_month="2026-09", expected_sha256=sha,
                       expected_rows=1, min_cell=1)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve original")

    def test_strict_cohort_accepts_valid_and_blank_closure_dates(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source.csv", Path(tmp) / "output.json"
            with source.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(FIELDS)
                writer.writerow(["fixture-1", "2026-09-10T09:00:00.000",
                                 "2026-09-11T09:00:00.000", "DOT",
                                 "Synthetic", "Queens", "Closed"])
                writer.writerow(["fixture-2", "2026-09-10T09:00:00.000",
                                 "", "DOT", "Synthetic", "Queens", "Open"])
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            result = ingest(source, output, as_of="2026-10-25",
                            reporting_month="2026-09", expected_sha256=sha,
                            expected_rows=2, min_cell=1)
            self.assertEqual(result["quality"]["unique_keys_verified"], 2)
            self.assertEqual(result["aggregates"][0]["requests"], 2)
            self.assertEqual(result["aggregates"][0]["closed_with_valid_interval"], 1)


if __name__ == "__main__": unittest.main()
