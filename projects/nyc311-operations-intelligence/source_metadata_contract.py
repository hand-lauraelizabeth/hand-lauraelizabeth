"""Offline fail-closed schema check for the NYC 311 2020-present publisher view.

Validates a previously obtained Socrata /api/views/erm2-nwe9 JSON object.
This is NOT network retrieval, proof of publisher origin, immutable snapshot
attestation, row reconciliation, privacy clearance, or publication approval.
"""
import hashlib
import json

VIEW_ID = "erm2-nwe9"
VIEW_NAME = "311 Service Requests from 2020 to Present"
REQUIRED_TYPES = {
    "unique_key": "text",
    "created_date": "calendar_date",  # Socrata API name for floating timestamp
    "closed_date": "calendar_date",
    "agency": "text",
    "complaint_type": "text",  # Displayed as Problem since 2025
    "borough": "text",
    "status": "text",
}


class MetadataContractError(ValueError):
    """Metadata cannot safely support the pinned 311 export contract."""


def validate_metadata(metadata):
    """Return a deterministic non-authenticating schema receipt or fail closed.

    Do not pin total column count: publisher can add unrelated columns. Never
    accept display labels (e.g. Problem) in place of backend field names.
    """
    if not isinstance(metadata, dict):
        raise MetadataContractError("METADATA_NOT_OBJECT")
    if metadata.get("id") != VIEW_ID or metadata.get("name") != VIEW_NAME:
        raise MetadataContractError("VIEW_IDENTITY_MISMATCH")
    columns = metadata.get("columns")
    if not isinstance(columns, list) or not columns:
        raise MetadataContractError("MISSING_COLUMNS")
    fields = {}
    for col in columns:
        if not isinstance(col, dict):
            raise MetadataContractError("INVALID_COLUMN")
        field = col.get("fieldName")
        dtype = col.get("dataTypeName")
        if not isinstance(field, str) or not field or not isinstance(dtype, str) or not dtype:
            raise MetadataContractError("INVALID_COLUMN")
        if field in fields:
            raise MetadataContractError("DUPLICATE_FIELD_NAME")
        fields[field] = dtype
    for field, expected in REQUIRED_TYPES.items():
        if field not in fields:
            raise MetadataContractError("REQUIRED_FIELD_MISSING")
        if fields[field] != expected:
            raise MetadataContractError("REQUIRED_FIELD_TYPE_CHANGED")
    # Socrata identifies its row key by a numeric column ID, not by a
    # human-readable display label. Check it when the publisher supplies it;
    # an absent declaration is explicitly NOT verified.
    row_identifier_verified = False
    if "rowIdentifierColumnId" in metadata:
        row_id = metadata["rowIdentifierColumnId"]
        key_column = next(col for col in columns if col["fieldName"] == "unique_key")
        key_id = key_column.get("id")
        if (type(row_id) is not int or type(key_id) is not int
                or row_id != key_id
                or sum(type(col.get("id")) is int and col.get("id") == row_id
                       for col in columns) != 1):
            raise MetadataContractError("ROW_IDENTIFIER_NOT_UNIQUE_KEY")
        row_identifier_verified = True

    selected = [[name, fields[name]] for name in sorted(REQUIRED_TYPES)]
    digest = hashlib.sha256(json.dumps(selected, separators=(",", ":")).encode()).hexdigest()
    return {
        "view_id": VIEW_ID,
        "required_field_count": len(REQUIRED_TYPES),
        "publisher_column_count": len(fields),
        "required_schema_sha256": digest,
        "row_identifier_unique_key_verified": row_identifier_verified,
        "verified_offline_only": True,
        "publisher_origin_authenticated": False,
        "publication_authorized": False,
    }
