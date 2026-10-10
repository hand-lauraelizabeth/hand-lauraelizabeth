"""Synthetic fixtures for the repository-level publication audit."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "repository_publication_gate.py"
spec = importlib.util.spec_from_file_location("publication_gate", path)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.project = self.root / gate.PROJECT
        self.project.mkdir(parents=True)

    def add(self, name):
        file = self.project / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("synthetic fixture", encoding="utf-8")

    def test_synthetic_explorer_is_allowed(self):
        self.add("public-explorer.html")
        self.assertEqual(gate.inspect_repository(self.root), [])

    def test_manifest_is_allowed(self):
        self.add("data/national/manifest.v1.json")
        self.assertEqual(gate.inspect_repository(self.root), [])

    def test_python_module_is_allowed(self):
        self.add("private_review/module.py")
        self.assertEqual(gate.inspect_repository(self.root), [])

    def test_national_shard_is_blocked(self):
        self.add("data/national/national-00.json")
        self.assertTrue(gate.inspect_repository(self.root))

    def test_ny_reference_is_blocked(self):
        self.add("ny-pilot-20-public-reference.json")
        self.assertTrue(gate.inspect_repository(self.root))

    def test_ny_html_fragment_is_blocked(self):
        self.add("ny-pilot-20-directory.fragment.html")
        self.assertTrue(gate.inspect_repository(self.root))

    def test_nested_csv_is_blocked(self):
        self.add("private_review/exports/records.csv")
        self.assertTrue(gate.inspect_repository(self.root))

    def test_gzip_is_blocked(self):
        self.add("data/sprint1/records.json.gz")
        self.assertTrue(gate.inspect_repository(self.root))

    def test_unanticipated_format_is_blocked(self):
        self.add("data/institutions.parquet")
        self.assertTrue(gate.inspect_repository(self.root))

    def test_missing_project_fails_closed(self):
        self.assertTrue(gate.inspect_repository(self.root / "nonexistent"))


if __name__ == "__main__":
    unittest.main()
