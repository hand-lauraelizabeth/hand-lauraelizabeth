"""Fail-closed metadata preflight for the official NYC 311 Socrata dataset.

The 2026-10-16 live metadata identifies created_date and closed_date as
calendar_date. The SODA API still serializes them as date-time strings.


Only public dataset metadata is requested; no service-request records are read.
"""
import hashlib
import json
import os
from urllib.request import Request, urlopen

DATASET_ID = "erm2-nwe9"
METADATA_URL = "https://data.cityofnewyork.us/api/views/erm2-nwe9"
REQUIRED_TYPES = {
    "unique_key": "text",
    "created_date": "calendar_date",
    "closed_date": "calendar_date",
    "agency": "text",
    "complaint_type": "text",
    "borough": "text",
    "status": "text",
}
MAX_METADATA_BYTES = 2_000_000


def validate_schema(metadata):
    """Validate source identity and all fields used by the private exporter."""
    if not isinstance(metadata, dict) or metadata.get("id") != DATASET_ID:
        raise ValueError("Unexpected NYC 311 dataset identity")
    columns = metadata.get("columns")
    if not isinstance(columns, list):
        raise ValueError("Missing NYC 311 columns metadata")
    observed = {}
    for column in columns:
        if not isinstance(column, dict):
            raise ValueError("Invalid NYC 311 column metadata")
        name = column.get("fieldName")
        if name in REQUIRED_TYPES:
            if name in observed:
                raise ValueError("Duplicate required NYC 311 column: " + name)
            observed[name] = column.get("dataTypeName")
    for name, expected_type in REQUIRED_TYPES.items():
        if name not in observed:
            raise ValueError("Missing required NYC 311 column: " + name)
        if observed[name] != expected_type:
            raise ValueError("Unexpected NYC 311 type for " + name)
    canonical = json.dumps(observed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "dataset_id": DATASET_ID,
        "metadata_url": METADATA_URL,
        "required_column_types": dict(sorted(observed.items())),
        "required_schema_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def fetch_schema(*, opener=urlopen):
    headers = {"Accept": "application/json", "User-Agent": "NYC311-Research-Export/1.0"}
    token = os.getenv("SOCRATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
    request = Request(METADATA_URL, headers=headers)
    with opener(request, timeout=30) as response:
        raw = response.read(MAX_METADATA_BYTES + 1)
    if len(raw) > MAX_METADATA_BYTES:
        raise ValueError("NYC 311 metadata exceeds size budget")
    try:
        metadata = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid NYC 311 metadata JSON") from exc
    return validate_schema(metadata)
