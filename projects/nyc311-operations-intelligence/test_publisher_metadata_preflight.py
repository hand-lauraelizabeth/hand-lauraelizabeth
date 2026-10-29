"""Synthetic-only regression tests for publisher metadata capture preflight."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "publisher_metadata_preflight", HERE / "publisher_metadata_preflight.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def fixture():
    names = gate.REQUIRED
    columns = [
        {"id": i + 1, "fieldName": name, "dataTypeName": kind}
        for i, (name, kind) in enumerate(names.items())
    ]
    return {"id": "erm2-nwe9", "provenance": "official",
            "assetType": "dataset", "publicationStage": "published",
            "rowsUpdatedAt": 1793237699,
            "rowIdentifierColumnId": 1, "columns": columns}


class PublisherMetadataPreflightTests(unittest.TestCase):
    def test_identical_receipts_are_stable_but_not_release_approval(self):
        x = fixture()
        self.assertEqual(gate.inspect_pair(x, copy.deepcopy(x)), [])

    def test_row_revision_drift_fails(self):
        x, y = fixture(), fixture()
        y["rowsUpdatedAt"] += 1
        self.assertIn("publisher_rows_revision_changed", gate.inspect_pair(x, y))

    def test_added_field_fails(self):
        x, y = fixture(), fixture()
        y["columns"].append({"id": 99, "fieldName": "new_field", "dataTypeName": "text"})
        self.assertIn("publisher_schema_changed", gate.inspect_pair(x, y))

    def test_required_field_type_change_fails(self):
        x, y = fixture(), fixture()
        y["columns"][1]["dataTypeName"] = "text"
        issues = gate.inspect_pair(x, y)
        self.assertIn("missing_or_changed_required_field", issues)
        self.assertIn("publisher_schema_changed", issues)

    def test_wrong_dataset_fails(self):
        y = fixture()
        y["id"] = "other-id"
        self.assertIn("unverified_publisher_identity", gate.inspect_pair(fixture(), y))

    def test_unofficial_provenance_fails(self):
        y = fixture()
        y["provenance"] = "community"
        self.assertIn("unverified_publisher_identity", gate.inspect_pair(fixture(), y))

    def test_unpublished_fails(self):
        y = fixture()
        y["publicationStage"] = "unpublished"
        self.assertIn("unpublished_source", gate.inspect_pair(fixture(), y))

    def test_duplicate_field_name_fails(self):
        y = fixture()
        y["columns"].append({"id": 98, "fieldName": "status", "dataTypeName": "text"})
        self.assertIn("duplicate_api_field", gate.inspect_pair(fixture(), y))

    def test_duplicate_column_id_fails(self):
        y = fixture()
        y["columns"].append({"id": 1, "fieldName": "extra", "dataTypeName": "text"})
        self.assertIn("duplicate_column_id", gate.inspect_pair(fixture(), y))

    def test_changed_row_identifier_fails(self):
        y = fixture()
        y["rowIdentifierColumnId"] = 2
        issues = gate.inspect_pair(fixture(), y)
        self.assertIn("unverified_unique_key_identifier", issues)
        self.assertIn("row_identifier_changed", issues)

    def test_missing_revision_fails(self):
        y = fixture()
        y.pop("rowsUpdatedAt")
        self.assertIn("invalid_rows_revision", gate.inspect_pair(fixture(), y))

    def test_api_computed_fields_do_not_conflict_with_portal_count(self):
        x = fixture()
        for i in range(7, 44):
            x["columns"].append({"id": i + 1, "fieldName": "synthetic_" + str(i),
                                 "dataTypeName": "text"})
        for i in range(4):
            x["columns"].append({"id": 100 + i, "fieldName": ":@computed_region_" + str(i),
                                 "dataTypeName": "number"})
        self.assertEqual(len(x["columns"]), 48)
        self.assertEqual(gate.inspect_pair(x, copy.deepcopy(x)), [])

    def test_nonkey_column_id_change_is_schema_drift(self):
        x, y = fixture(), fixture()
        # Unique Key's identifier is stable, so the old name/type-only
        # fingerprint silently accepted this replacement.
        y["columns"][3]["id"] = 99
        self.assertIn("publisher_schema_changed", gate.inspect_pair(x, y))

    def test_nonkey_column_id_swap_is_schema_drift(self):
        x, y = fixture(), fixture()
        y["columns"][3]["id"], y["columns"][4]["id"] = (
            y["columns"][4]["id"], y["columns"][3]["id"])
        self.assertIn("publisher_schema_changed", gate.inspect_pair(x, y))

    def test_asset_type_change_fails(self):
        x, y = fixture(), fixture()
        y["assetType"] = "filter"
        self.assertIn("invalid_publisher_asset_type", gate.inspect_pair(x, y))

    def test_nonpositive_column_id_fails(self):
        x, y = fixture(), fixture()
        y["columns"][3]["id"] = 0
        self.assertIn("invalid_column_id", gate.inspect_pair(x, y))

    def test_unhashable_row_identifier_fails_closed(self):
        x, y = fixture(), fixture()
        y["rowIdentifierColumnId"] = {"unexpected": "value"}
        self.assertIn("unverified_unique_key_identifier", gate.inspect_pair(x, y))

    def test_cli_stable_is_not_release_authorization(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.json", Path(d) / "b.json"
            a.write_text(json.dumps(fixture()), encoding="utf-8")
            b.write_text(json.dumps(fixture()), encoding="utf-8")
            self.assertEqual(gate.main([str(a), str(b)]), 0)

    def test_cli_unreadable_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.json"
            a.write_text("{", encoding="utf-8")
            self.assertEqual(gate.main([str(a), str(Path(d) / "missing.json")]), 2)


if __name__ == "__main__":
    unittest.main()
