"""Synthetic adversarial checks for the optional Socrata row identifier declaration.

These tests use no source records and do not establish publisher provenance.
"""
import unittest

from source_metadata_contract import (
    MetadataContractError, REQUIRED_TYPES, validate_metadata,
)


def fixture():
    columns = [
        {"fieldName": name, "dataTypeName": dtype, "name": name, "id": 500 + index}
        for index, (name, dtype) in enumerate(REQUIRED_TYPES.items())
    ]
    return {
        "id": "erm2-nwe9",
        "name": "311 Service Requests from 2020 to Present",
        "columns": columns,
        "rowIdentifierColumnId": 500,
    }


class RowIdentifierContractTests(unittest.TestCase):
    def test_declared_unique_key_matches(self):
        self.assertTrue(validate_metadata(fixture())["row_identifier_unique_key_verified"])

    def test_absent_declaration_not_misreported_as_verified(self):
        data = fixture()
        del data["rowIdentifierColumnId"]
        self.assertFalse(validate_metadata(data)["row_identifier_unique_key_verified"])

    def test_declared_different_field_rejected(self):
        data = fixture()
        data["rowIdentifierColumnId"] = 501
        with self.assertRaisesRegex(MetadataContractError, "ROW_IDENTIFIER_NOT_UNIQUE_KEY"):
            validate_metadata(data)

    def test_missing_unique_key_column_id_rejected(self):
        data = fixture()
        del data["columns"][0]["id"]
        with self.assertRaisesRegex(MetadataContractError, "ROW_IDENTIFIER_NOT_UNIQUE_KEY"):
            validate_metadata(data)

    def test_boolean_row_identifier_rejected(self):
        data = fixture()
        data["rowIdentifierColumnId"] = True
        with self.assertRaisesRegex(MetadataContractError, "ROW_IDENTIFIER_NOT_UNIQUE_KEY"):
            validate_metadata(data)

    def test_string_row_identifier_rejected(self):
        data = fixture()
        data["rowIdentifierColumnId"] = "500"
        with self.assertRaisesRegex(MetadataContractError, "ROW_IDENTIFIER_NOT_UNIQUE_KEY"):
            validate_metadata(data)

    def test_duplicate_column_id_rejected(self):
        data = fixture()
        data["columns"][1]["id"] = 500
        with self.assertRaisesRegex(MetadataContractError, "ROW_IDENTIFIER_NOT_UNIQUE_KEY"):
            validate_metadata(data)

    def test_unrelated_new_column_does_not_change_row_identifier(self):
        data = fixture()
        data["columns"].append({"fieldName": "new_field", "dataTypeName": "text", "id": 999})
        result = validate_metadata(data)
        self.assertTrue(result["row_identifier_unique_key_verified"])
        self.assertEqual(result["publisher_column_count"], 8)


if __name__ == "__main__":
    unittest.main()
