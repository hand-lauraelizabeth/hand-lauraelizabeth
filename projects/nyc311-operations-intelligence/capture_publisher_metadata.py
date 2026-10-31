"""Acquire a PRIVATE byte-level HTTP receipt for public NYC 311 view metadata.

No service-request rows are requested. The raw metadata file may contain public
column samples; never commit it or publish it. A receipt is NOT an immutable
publisher attestation or a September 2026 CSV reconciliation.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from source_metadata_contract import MetadataContractError, validate_metadata

SOURCE_URL = "https://data.cityofnewyork.us/api/views/erm2-nwe9.json"
MAX_BODY_BYTES = 8 * 1024 * 1024


class AcquisitionError(ValueError):
    """Reject untrustworthy or unexpected HTTP metadata acquisitions."""


def acquire_metadata(opener=None, now=None):
    """Return (exact raw response bytes, private receipt); no disk writes.

    opener is injectable for synthetic tests. The default urllib HTTPS opener
    verifies TLS certificates against the runtime trust store, but this alone
    is not independent publisher-origin attestation.
    """
    opener = urlopen if opener is None else opener
    req = Request(SOURCE_URL, headers={
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "NYC311-Private-Metadata-Receipt/1.0",
    })
    with opener(req, timeout=20) as response:
        if response.status != 200:
            raise AcquisitionError("HTTP_STATUS_NOT_200")
        if response.geturl() != SOURCE_URL:
            raise AcquisitionError("REDIRECT_OR_SOURCE_URL_CHANGED")
        headers = response.headers
        content_type = (headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise AcquisitionError("NOT_JSON_CONTENT_TYPE")
        encoding = (headers.get("Content-Encoding") or "identity").strip().lower()
        if encoding != "identity":
            raise AcquisitionError("UNEXPECTED_CONTENT_ENCODING")
        declared = headers.get("Content-Length")
        if declared is not None:
            try:
                declared_size = int(declared)
            except (TypeError, ValueError) as exc:
                raise AcquisitionError("INVALID_CONTENT_LENGTH") from exc
            if declared_size < 1 or declared_size > MAX_BODY_BYTES:
                raise AcquisitionError("DECLARED_SIZE_OUT_OF_BOUNDS")
        raw = response.read(MAX_BODY_BYTES + 1)
        if not raw or len(raw) > MAX_BODY_BYTES:
            raise AcquisitionError("BODY_SIZE_OUT_OF_BOUNDS")
        if declared is not None and len(raw) != declared_size:
            raise AcquisitionError("CONTENT_LENGTH_MISMATCH")
        etag = headers.get("ETag")
        last_modified = headers.get("Last-Modified")
    try:
        metadata = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise AcquisitionError("INVALID_JSON_BODY") from exc
    try:
        schema = validate_metadata(metadata)
    except MetadataContractError as exc:
        raise AcquisitionError("METADATA_CONTRACT_FAILED:" + str(exc)) from exc
    observed = datetime.now(timezone.utc) if now is None else now
    if observed.tzinfo is None:
        raise AcquisitionError("NAIVE_CAPTURE_TIME")
    receipt = {
        "record_type": "private_http_metadata_acquisition",
        "source_url": SOURCE_URL,
        "captured_at_utc": observed.astimezone(timezone.utc).isoformat(),
        "http_status": 200,
        "content_type": content_type,
        "etag": etag,
        "last_modified": last_modified,
        "raw_body_bytes": len(raw),
        "raw_body_sha256": hashlib.sha256(raw).hexdigest(),
        "dataset_id": schema["view_id"],
        "required_schema_sha256": schema["required_schema_sha256"],
        "required_field_count": schema["required_field_count"],
        "observed_metadata_columns": schema["publisher_column_count"],
        "transport_method": "urllib HTTPS, default CA verification (not independently attested)",
        "publisher_origin_authenticated": False,
        "september_csv_reconciled": False,
        "disclosure_approved": False,
        "publication_authorized": False,
        "limitations": [
            "Raw metadata and receipt are local/private; never commit raw metadata.",
            "A successful HTTPS response and SHA-256 do not establish a signed or immutable publisher snapshot.",
            "No 311 service-request records, September CSV, unique-key counts, or privacy release gates were checked.",
        ],
    }
    return raw, receipt


def _write_private_new(path, data):
    """Create only; do not overwrite an earlier acquisition."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", required=True, help="Private output directory, never the public repository")
    args = parser.parse_args()
    target = Path(args.private_dir).expanduser().resolve()
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    raw, receipt = acquire_metadata()
    stamp = receipt["captured_at_utc"].replace("-", "").replace(":", "").replace("+00:00", "Z").split(".")[0]
    prefix = "nyc311_metadata_" + stamp
    _write_private_new(target / (prefix + "_raw.json"), raw)
    _write_private_new(target / (prefix + "_receipt.json"),
                       (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({k: receipt[k] for k in (
        "source_url", "captured_at_utc", "raw_body_bytes", "raw_body_sha256",
        "required_field_count", "publisher_origin_authenticated", "publication_authorized"
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
