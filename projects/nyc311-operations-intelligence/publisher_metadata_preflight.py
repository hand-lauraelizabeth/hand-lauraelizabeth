"""Offline NYC 311 publisher-metadata preflight; never authorizes publication.

Capture the official /api/views/erm2-nwe9 JSON immediately before and after
the separately authenticated CSV export. This checks that the advertised row
revision and API schema did not change across the capture window. It CANNOT
prove transactional consistency, exact unique-key membership, or privacy.
No record-level source data or raw metadata receipts belong in this repository.
"""
import argparse
import json
from pathlib import Path

DATASET = "erm2-nwe9"
REQUIRED = {
    "unique_key": "text",
    "created_date": "calendar_date",
    "closed_date": "calendar_date",
    "agency": "text",
    "complaint_type": "text",
    "borough": "text",
    "status": "text",
}


def fingerprint(metadata):
    """Return (public schema signature, publisher revision) or issue codes."""
    issues = set()
    if not isinstance(metadata, dict):
        return None, None, ["invalid_metadata"]
    if metadata.get("id") != DATASET or metadata.get("provenance") != "official":
        issues.add("unverified_publisher_identity")
    if metadata.get("publicationStage") != "published":
        issues.add("unpublished_source")
    if metadata.get("assetType") != "dataset":
        issues.add("invalid_publisher_asset_type")
    revision = metadata.get("rowsUpdatedAt")
    if type(revision) is not int or revision <= 0:
        issues.add("invalid_rows_revision")
    cols = metadata.get("columns")
    if not isinstance(cols, list) or not cols:
        return None, None, sorted(issues | {"invalid_schema"})
    names = {}
    ids = {}
    for col in cols:
        if not isinstance(col, dict):
            issues.add("invalid_schema")
            continue
        name, kind, cid = col.get("fieldName"), col.get("dataTypeName"), col.get("id")
        if not isinstance(name, str) or not name or not isinstance(kind, str):
            issues.add("invalid_schema")
            continue
        if name in names:
            issues.add("duplicate_api_field")
        names[name] = (cid, kind)
        if type(cid) is not int or cid <= 0:
            issues.add("invalid_column_id")
        elif cid in ids:
            issues.add("duplicate_column_id")
        else:
            ids[cid] = name
    for name, kind in REQUIRED.items():
        if names.get(name, (None, None))[1] != kind:
            issues.add("missing_or_changed_required_field")
    identifier = metadata.get("rowIdentifierColumnId")
    if type(identifier) is not int or ids.get(identifier) != "unique_key":
        issues.add("unverified_unique_key_identifier")
    # Include computed region fields in signature, but do not require the
    # portal's 44 displayed columns to equal the API's 48 metadata columns.
    # Column IDs are part of publisher schema identity: stable names/types
    # alone can conceal an API-column replacement during an export.
    signature = tuple(sorted((name, cid, kind)
                             for name, (cid, kind) in names.items()))
    return signature, revision, sorted(issues)


def inspect_pair(before, after):
    """Return redacted HOLD reasons; a clean result is NOT release approval."""
    a, ar, ai = fingerprint(before)
    b, br, bi = fingerprint(after)
    issues = set(ai + bi)
    if a is not None and b is not None and a != b:
        issues.add("publisher_schema_changed")
    if type(ar) is int and type(br) is int and ar != br:
        issues.add("publisher_rows_revision_changed")
    if (isinstance(before, dict) and isinstance(after, dict)
            and before.get("rowIdentifierColumnId") != after.get("rowIdentifierColumnId")):
        issues.add("row_identifier_changed")
    return sorted(issues)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args(argv)
    try:
        before = json.loads(args.before.read_text(encoding="utf-8"))
        after = json.loads(args.after.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        print("HOLD: invalid_or_unreadable_receipt")
        return 2
    issues = inspect_pair(before, after)
    if issues:
        print("HOLD: " + ", ".join(issues))
        return 2
    print("METADATA_STABLE_ONLY: source authentication, exact-key audit, and disclosure review remain HOLD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
