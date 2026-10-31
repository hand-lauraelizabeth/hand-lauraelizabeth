"""Offline adversarial tests for the PRIVATE NYC 311 HTTP metadata capture.

No network, public service-request rows, or publisher authentication claims.
"""
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from capture_publisher_metadata import (
    AcquisitionError, MAX_BODY_BYTES, SOURCE_URL, acquire_metadata,
    _ensure_private_dir,
)
from source_metadata_contract import REQUIRED_TYPES


def valid_metadata():
    return {
        "id": "erm2-nwe9",
        "name": "311 Service Requests from 2020 to Present",
        "columns": [
            {"fieldName": field, "dataTypeName": kind, "name": field}
            for field, kind in REQUIRED_TYPES.items()
        ],
    }


class Response(io.BytesIO):
    def __init__(self, body, status=200, url=SOURCE_URL, headers=None):
        super().__init__(body)
        self.status = status
        self._url = url
        self.headers = headers or {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body)),
            "ETag": '"test-etag"',
            "Last-Modified": "Sat, 31 Oct 2026 20:00:00 GMT",
        }

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def mock_acquire(payload=None, **kwargs):
    if payload is None:
        payload = valid_metadata()
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    return acquire_metadata(
        opener=lambda req, timeout: Response(body, **kwargs),
        now=datetime(2026, 10, 31, 21, 0, tzinfo=timezone.utc),
    )


class PrivateDirectorySafetyTests(unittest.TestCase):
    def test_new_private_directory_created_with_restrictive_permissions(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "private" / "receipts"
            _ensure_private_dir(target)
            self.assertEqual(target.stat().st_mode & 0o777, 0o700)

    def test_existing_secure_directory_is_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "private"
            target.mkdir(mode=0o700)
            _ensure_private_dir(target)

    def test_existing_world_readable_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "public"
            target.mkdir()
            os.chmod(target, 0o755)
            with self.assertRaisesRegex(AcquisitionError, "PRIVATE_DIRECTORY_PERMISSIONS_UNSAFE"):
                _ensure_private_dir(target)

    def test_git_checkout_destination_is_rejected_even_if_private(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "checkout"
            repo.mkdir(mode=0o700)
            (repo / ".git").write_text("gitdir: /tmp/example\\n")
            target = repo / "private"
            with self.assertRaisesRegex(AcquisitionError, "PRIVATE_DIRECTORY_INSIDE_GIT_CHECKOUT"):
                _ensure_private_dir(target)


class PrivateHttpMetadataReceiptTests(unittest.TestCase):
    def test_valid_receipt_records_exact_bytes_and_no_release(self):
        raw, receipt = mock_acquire()
        self.assertEqual(receipt["raw_body_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt["raw_body_bytes"], len(raw))
        self.assertEqual(receipt["required_field_count"], 7)
        self.assertEqual(receipt["observed_metadata_columns"], 7)
        self.assertEqual(receipt["captured_at_utc"], "2026-10-31T21:00:00+00:00")
        for key in ("publisher_origin_authenticated", "september_csv_reconciled",
                    "disclosure_approved", "publication_authorized"):
            self.assertFalse(receipt[key])
        self.assertNotIn("rows", receipt)

    def test_expected_source_request_is_pinned_https_metadata_only(self):
        def opener(req, timeout):
            self.assertEqual(req.full_url, SOURCE_URL)
            self.assertEqual(req.get_header("Accept-encoding"), "identity")
            self.assertEqual(timeout, 20)
            body = json.dumps(valid_metadata()).encode()
            return Response(body)
        raw, _ = acquire_metadata(opener=opener)
        self.assertTrue(raw.startswith(b"{"))

    def test_unrelated_added_column_is_permitted(self):
        payload = valid_metadata()
        payload["columns"].append({"fieldName": "new_column", "dataTypeName": "text"})
        _, receipt = mock_acquire(payload)
        self.assertEqual(receipt["observed_metadata_columns"], 8)

    def test_wrong_dataset_rejected(self):
        payload = valid_metadata()
        payload["id"] = "76ig-c548"
        with self.assertRaisesRegex(AcquisitionError, "METADATA_CONTRACT_FAILED"):
            mock_acquire(payload)

    def test_required_type_drift_rejected(self):
        payload = valid_metadata()
        payload["columns"][1]["dataTypeName"] = "text"
        with self.assertRaisesRegex(AcquisitionError, "METADATA_CONTRACT_FAILED"):
            mock_acquire(payload)

    def test_non_200_http_status_rejected(self):
        with self.assertRaisesRegex(AcquisitionError, "HTTP_STATUS_NOT_200"):
            mock_acquire(status=206)

    def test_redirect_or_wrong_host_rejected(self):
        with self.assertRaisesRegex(AcquisitionError, "REDIRECT_OR_SOURCE_URL_CHANGED"):
            mock_acquire(url="https://example.com/api/views/erm2-nwe9.json")

    def test_wrong_mime_rejected(self):
        with self.assertRaisesRegex(AcquisitionError, "NOT_JSON_CONTENT_TYPE"):
            mock_acquire(headers={"Content-Type": "text/html"})

    def test_compressed_body_rejected(self):
        with self.assertRaisesRegex(AcquisitionError, "UNEXPECTED_CONTENT_ENCODING"):
            mock_acquire(headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})

    def test_oversized_declared_body_rejected_without_reading(self):
        with self.assertRaisesRegex(AcquisitionError, "DECLARED_SIZE_OUT_OF_BOUNDS"):
            mock_acquire(headers={"Content-Type": "application/json",
                                  "Content-Length": str(MAX_BODY_BYTES + 1)})

    def test_mismatched_content_length_rejected(self):
        with self.assertRaisesRegex(AcquisitionError, "CONTENT_LENGTH_MISMATCH"):
            mock_acquire(headers={"Content-Type": "application/json", "Content-Length": "1"})

    def test_invalid_length_header_rejected(self):
        with self.assertRaisesRegex(AcquisitionError, "INVALID_CONTENT_LENGTH"):
            mock_acquire(headers={"Content-Type": "application/json", "Content-Length": "not-a-number"})

    def test_malformed_json_rejected(self):
        with self.assertRaisesRegex(AcquisitionError, "INVALID_JSON_BODY"):
            acquire_metadata(opener=lambda req, timeout: Response(b"{not-json"))

    def test_naive_timestamp_rejected(self):
        body = json.dumps(valid_metadata()).encode()
        with self.assertRaisesRegex(AcquisitionError, "NAIVE_CAPTURE_TIME"):
            acquire_metadata(opener=lambda req, timeout: Response(body),
                             now=datetime(2026, 10, 31, 21, 0))

    def test_raw_body_cap_rejected_even_without_content_length(self):
        with self.assertRaisesRegex(AcquisitionError, "BODY_SIZE_OUT_OF_BOUNDS"):
            acquire_metadata(opener=lambda req, timeout: Response(
                b"x" * (MAX_BODY_BYTES + 1),
                headers={"Content-Type": "application/json"},
            ))

    def test_no_network_or_disk_io_during_mocked_acquisition(self):
        with patch("capture_publisher_metadata.urlopen", side_effect=AssertionError("network")):
            raw, receipt = mock_acquire()
        self.assertEqual(receipt["raw_body_bytes"], len(raw))


if __name__ == "__main__":
    unittest.main()
