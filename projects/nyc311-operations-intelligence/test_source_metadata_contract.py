"""Synthetic-only adversarial tests for the NYC 311 source schema gate."""
import copy
import unittest

from source_metadata_contract import MetadataContractError, REQUIRED_TYPES, validate_metadata


def fixture():
    return {
        "id": "erm2-nwe9",
        "name": "311 Service Requests from 2020 to Present",
        "columns": [
            {"fieldName": key, "dataTypeName": dtype, "name": key}
            for key, dtype in REQUIRED_TYPES.items()
        ],
    }


class SourceMetadataContractTests(unittest.TestCase):
    def test_valid_publisher_contract_offline_only(self):
        receipt = validate_metadata(fixture())
        self.assertEqual(receipt["required_field_count"], 7)
        self.assertEqual(receipt["publisher_column_count"], 7)
        self.assertFalse(receipt["publisher_origin_authenticated"])
        self.assertFalse(receipt["publication_authorized"])
        self.assertEqual(len(receipt["required_schema_sha256"]), 64)

    def test_additive_unrelated_column_is_allowed(self):
        data = fixture()
        original = validate_metadata(data)["required_schema_sha256"]
        data["columns"].append({"fieldName": "council_district", "dataTypeName": "text"})
        receipt = validate_metadata(data)
        self.assertEqual(receipt["publisher_column_count"], 8)
        self.assertEqual(receipt["required_schema_sha256"], original)

    def test_column_order_is_not_semantic(self):
        data = fixture()
        original = validate_metadata(data)["required_schema_sha256"]
        data["columns"].reverse()
        self.assertEqual(validate_metadata(data)["required_schema_sha256"], original)

    def test_wrong_view_id_rejected_even_with_same_columns(self):
        data = fixture()
        data["id"] = "76ig-c548"  # Separate historical 2010–2019 archive
        with self.assertRaisesRegex(MetadataContractError, "VIEW_IDENTITY_MISMATCH"):
            validate_metadata(data)

    def test_wrong_view_name_rejected(self):
        data = fixture()
        data["name"] = "311 Service Requests from 2010 to Present"
        with self.assertRaisesRegex(MetadataContractError, "VIEW_IDENTITY_MISMATCH"):
            validate_metadata(data)

    def test_missing_required_field_rejected(self):
        for field in REQUIRED_TYPES:
            with self.subTest(field=field):
                data = fixture()
                data["columns"] = [c for c in data["columns"] if c["fieldName"] != field]
                with self.assertRaisesRegex(MetadataContractError, "REQUIRED_FIELD_MISSING"):
                    validate_metadata(data)

    def test_display_name_cannot_replace_backend_field(self):
        data = fixture()
        next(c for c in data["columns"] if c["fieldName"] == "complaint_type")["fieldName"] = "Problem"
        with self.assertRaisesRegex(MetadataContractError, "REQUIRED_FIELD_MISSING"):
            validate_metadata(data)

    def test_timestamp_type_change_rejected(self):
        for field in ("created_date", "closed_date"):
            with self.subTest(field=field):
                data = fixture()
                next(c for c in data["columns"] if c["fieldName"] == field)["dataTypeName"] = "text"
                with self.assertRaisesRegex(MetadataContractError, "REQUIRED_FIELD_TYPE_CHANGED"):
                    validate_metadata(data)

    def test_duplicate_field_rejected(self):
        data = fixture()
        data["columns"].append(copy.deepcopy(data["columns"][0]))
        with self.assertRaisesRegex(MetadataContractError, "DUPLICATE_FIELD_NAME"):
            validate_metadata(data)

    def test_bad_column_shapes_rejected(self):
        for bad in (None, [], "not a list", [{"fieldName": "unique_key"}], [None]):
            with self.subTest(bad=bad):
                data = fixture()
                data["columns"] = bad
                with self.assertRaises(MetadataContractError):
                    validate_metadata(data)

    def test_non_object_rejected(self):
        for bad in (None, [], "json", 5):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(MetadataContractError, "METADATA_NOT_OBJECT"):
                    validate_metadata(bad)


if __name__ == "__main__":
    unittest.main()
