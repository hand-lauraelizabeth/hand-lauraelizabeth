"""Deterministic NYC 311 metadata-contract tests; no live requests."""
import io
import json
import unittest
from source_schema import REQUIRED_TYPES, MAX_METADATA_BYTES, fetch_schema, validate_schema


def valid_metadata():
    return {"id": "erm2-nwe9", "columns": [
        {"fieldName": name, "dataTypeName": dtype} for name, dtype in REQUIRED_TYPES.items()
    ] + [{"fieldName": "incident_address", "dataTypeName": "text"}]}


class FakeResponse:
    def __init__(self, data): self.stream = io.BytesIO(data)
    def __enter__(self): return self
    def __exit__(self, *_): self.stream.close()
    def read(self, size): return self.stream.read(size)


class SourceSchemaTests(unittest.TestCase):
    def test_valid_schema_and_stable_hash_independent_of_column_order(self):
        first = validate_schema(valid_metadata())
        swapped = valid_metadata()
        swapped["columns"].reverse()
        self.assertEqual(first, validate_schema(swapped))
        self.assertEqual(first["dataset_id"], "erm2-nwe9")
        self.assertEqual(len(first["required_column_types"]), 7)
        self.assertEqual(len(first["required_schema_sha256"]), 64)

    def test_official_2026_calendar_date_schema(self):
        # Independently observed at the official /api/views/erm2-nwe9 endpoint
        # on 2026-10-16; this is a pinned metadata fixture, not a live fetch.
        observed = {
            "unique_key": "text",
            "created_date": "calendar_date",
            "closed_date": "calendar_date",
            "agency": "text",
            "complaint_type": "text",
            "borough": "text",
            "status": "text",
        }
        self.assertEqual(REQUIRED_TYPES, observed)
        metadata = {"id": "erm2-nwe9", "columns": [
            {"fieldName": key, "dataTypeName": value}
            for key, value in observed.items()
        ]}
        result = validate_schema(metadata)
        self.assertEqual(result["required_column_types"], dict(sorted(observed.items())))
        # Fail closed on a genuinely changed date type.
        metadata["columns"][1]["dataTypeName"] = "floating_timestamp"
        with self.assertRaisesRegex(ValueError, "Unexpected.*created_date"):
            validate_schema(metadata)

    def test_wrong_dataset_rejected(self):
        value = valid_metadata()
        value["id"] = "unrelated"
        with self.assertRaisesRegex(ValueError, "dataset identity"):
            validate_schema(value)

    def test_missing_column_rejected(self):
        value = valid_metadata()
        value["columns"] = [c for c in value["columns"] if c["fieldName"] != "status"]
        with self.assertRaisesRegex(ValueError, "Missing required.*status"):
            validate_schema(value)

    def test_changed_type_rejected(self):
        value = valid_metadata()
        value["columns"][1]["dataTypeName"] = "text"
        with self.assertRaisesRegex(ValueError, "Unexpected.*created_date"):
            validate_schema(value)

    def test_duplicate_required_field_rejected(self):
        value = valid_metadata()
        value["columns"].append({"fieldName": "unique_key", "dataTypeName": "text"})
        with self.assertRaisesRegex(ValueError, "Duplicate required"):
            validate_schema(value)

    def test_missing_columns_metadata_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing.*columns"):
            validate_schema({"id": "erm2-nwe9"})

    def test_fetch_valid_metadata_with_mocked_opener(self):
        data = json.dumps(valid_metadata()).encode()
        def opener(request, timeout):
            self.assertEqual(timeout, 30)
            self.assertIn("/api/views/erm2-nwe9", request.full_url)
            return FakeResponse(data)
        self.assertEqual(fetch_schema(opener=opener)["dataset_id"], "erm2-nwe9")

    def test_fetch_rejects_malformed_json(self):
        with self.assertRaisesRegex(ValueError, "Invalid.*JSON"):
            fetch_schema(opener=lambda *_args, **_kw: FakeResponse(b"{invalid"))

    def test_fetch_rejects_oversize_metadata(self):
        with self.assertRaisesRegex(ValueError, "size budget"):
            fetch_schema(opener=lambda *_args, **_kw: FakeResponse(b"x" * (MAX_METADATA_BYTES + 1)))


if __name__ == "__main__": unittest.main()
