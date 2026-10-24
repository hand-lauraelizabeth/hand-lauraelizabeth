"""Private bounded capture of a reviewed NYC 311 CSV response.

A successful capture preserves bytes and transport metadata, not proof of
publisher provenance, an immutable snapshot, or permission to publish data.
Only the seven explicitly selected public-data fields are requested. Do not
commit downloaded source rows or capture receipts to a public repository.
"""
import argparse
import csv
from contextlib import closing
import io
from http.client import HTTPException
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from urllib.request import Request, HTTPRedirectHandler, build_opener

from source_export_query_contract import (check_export_query, query_fingerprint,
                                          canonical_export_url, FIELDS)

MAX_SOURCE_BYTES = 1024 * 1024 * 1024  # Keep in sync with private_release_gate.
CHUNK_BYTES = 1024 * 1024


class CaptureError(Exception):
    """Safe transport failure: never includes record-level data or query values."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _verify_selected_csv_header(path):
    """Reject any unrequested columns before exposing a private source file.

    The seven-field API export is intentionally minimal. This bounded first-
    line check is not a substitute for the full streaming row/key/month audit.
    """
    with Path(path).open('rb') as source:
        prefix = source.read(4096)
    if b'\n' not in prefix:
        raise CaptureError('SOURCE_CSV_HEADER_INVALID')
    try:
        first_line = prefix.split(b'\n', 1)[0] + b'\n'
        parsed = list(csv.reader(io.StringIO(first_line.decode('utf-8-sig')),
                                 strict=True))
    except (UnicodeError, csv.Error):
        raise CaptureError('SOURCE_CSV_HEADER_INVALID') from None
    if len(parsed) != 1 or parsed[0] != FIELDS.split(','):
        raise CaptureError('SOURCE_CSV_HEADER_INVALID')


def capture_official_csv(url, destination, *, reference_rows, opener=None,
                         timeout=60, max_bytes=MAX_SOURCE_BYTES, clock=None):
    """Save one exact, bounded HTTPS CSV response without replacing an existing file.

    The caller must run the separate CSV key/month audit and reconcile a
    contemporaneous publisher snapshot. A successful result is still HOLD.
    `opener`/`clock` are injectable for offline, synthetic regression tests.
    """
    if check_export_query(url, reference_rows=reference_rows) != [
            'SOURCE_QUERY_SHAPE_VERIFIED_NOT_PROVENANCE']:
        raise CaptureError('SOURCE_QUERY_NOT_VERIFIED')
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_SOURCE_BYTES:
        raise CaptureError('SOURCE_CAPTURE_LIMIT_INVALID')
    target = Path(destination)
    if target.exists() or target.is_symlink():
        raise CaptureError('SOURCE_DESTINATION_EXISTS')
    if not target.parent.is_dir():
        raise CaptureError('SOURCE_DESTINATION_PARENT_INVALID')
    if opener is None:
        opener = build_opener(_NoRedirect())
    request = Request(url, headers={
        'Accept': 'text/csv', 'Accept-Encoding': 'identity',
        'User-Agent': 'NYC311-Source-QA/1.0',
    })
    temporary = None
    try:
        with closing(opener.open(request, timeout=timeout)) as response:
            if response.status != 200:
                raise CaptureError('SOURCE_HTTP_STATUS_INVALID')
            if response.geturl() != url:
                raise CaptureError('SOURCE_HTTP_REDIRECT_OR_URL_MISMATCH')
            # A 200 response carrying Content-Range can still be a fragment.
            # A partial CSV must never be accepted as a complete source capture.
            if response.headers.get('Content-Range') is not None:
                raise CaptureError('SOURCE_HTTP_PARTIAL_RESPONSE_INVALID')
            media = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
            if media not in {'text/csv', 'application/csv'}:
                raise CaptureError('SOURCE_HTTP_CONTENT_TYPE_INVALID')
            encoding = response.headers.get('Content-Encoding', 'identity').strip().lower()
            if encoding not in ('', 'identity'):
                raise CaptureError('SOURCE_HTTP_ENCODING_INVALID')
            declared = response.headers.get('Content-Length')
            if declared is not None:
                if not declared.isascii() or not declared.isdecimal():
                    raise CaptureError('SOURCE_HTTP_LENGTH_INVALID')
                if int(declared) > max_bytes:
                    raise CaptureError('SOURCE_CAPTURE_SIZE_LIMIT_EXCEEDED')
            digest = sha256()
            size = 0
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.nyc311_capture_',
                                             suffix='.tmp', delete=False) as out:
                temporary = Path(out.name)
                while True:
                    chunk = response.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    if not isinstance(chunk, bytes):
                        raise CaptureError('SOURCE_HTTP_BODY_INVALID')
                    size += len(chunk)
                    if size > max_bytes:
                        raise CaptureError('SOURCE_CAPTURE_SIZE_LIMIT_EXCEEDED')
                    digest.update(chunk)
                    out.write(chunk)
                if size == 0 or (declared is not None and int(declared) != size):
                    raise CaptureError('SOURCE_HTTP_LENGTH_MISMATCH')
                out.flush()
                os.fsync(out.fileno())
        # Reject unexpected columns, including potentially identifying fields,
        # before exposing even a private capture destination.
        _verify_selected_csv_header(temporary)
        # Close the HTTP response before publishing a source file. A close-time
        # protocol error must not leave a seemingly successful orphan capture.
        # Atomic no-clobber link: never replace a user's source or report.
        captured = clock() if clock else datetime.now(timezone.utc)
        if not isinstance(captured, datetime) or captured.tzinfo is None:
            raise CaptureError('SOURCE_CAPTURE_CLOCK_INVALID')
        # Prepare the complete audit receipt before publishing the CSV.
        # If fingerprint or timestamp serialization fails, no destination
        # is exposed; the temporary capture is cleaned in finally.
        metadata = {
            'status': 'HOLD', 'source_origin_authenticated': False,
            'source_url': url, 'source_query_sha256': query_fingerprint(url),
            'source_sha256': digest.hexdigest(), 'source_bytes': size,
            'http_status': 200, 'content_type': media,
            'http_content_length': int(declared) if declared is not None else None,
            'captured_at_utc': captured.astimezone(timezone.utc).isoformat(),
            'required_next': 'independent_unique_key_month_count_privacy_and_source_review',
        }
        os.link(temporary, target)
        return metadata
    except CaptureError:
        raise
    except (OSError, ValueError, TypeError, HTTPException) as exc:
        raise CaptureError('SOURCE_HTTP_OR_DISK_FAILED_CLOSED') from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    """Explicit private capture command; never performs a release or publication."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-csv', required=True)
    parser.add_argument('--receipt-json', required=True)
    parser.add_argument('--reference-rows', type=int, required=True)
    parser.add_argument('--limit', type=int, default=400000)
    args = parser.parse_args(argv)
    source, receipt = Path(args.source_csv), Path(args.receipt_json)
    if (source.resolve() == receipt.resolve() or receipt.exists() or
            receipt.is_symlink() or not receipt.parent.is_dir()):
        print('HOLD: invalid or occupied receipt destination')
        return 2
    # The CSV and receipt form a private evidence pair. Never leave an orphan
    # source CSV when receipt persistence fails; never replace an existing receipt.
    # Stage the receipt in its destination directory and hard-link it only after
    # fsync. A staged receipt is not a published receipt.
    source_created = False
    receipt_committed = False
    staged_receipt = None
    try:
        metadata = capture_official_csv(
            canonical_export_url(limit=args.limit), source,
            reference_rows=args.reference_rows)
        source_created = True
        with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=receipt.parent,
                prefix='.nyc311_receipt_', suffix='.tmp', delete=False) as handle:
            staged_receipt = Path(handle.name)
            json.dump(metadata, handle, indent=2, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.link(staged_receipt, receipt)  # atomic, exclusive, no clobber
        receipt_committed = True
    except (CaptureError, ValueError, OSError, TypeError):
        if source_created and not receipt_committed:
            source.unlink(missing_ok=True)
        print('HOLD: source capture or receipt failed closed')
        return 2
    finally:
        if staged_receipt is not None:
            staged_receipt.unlink(missing_ok=True)
    print('HOLD: private source captured; provenance, row and disclosure QA required')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
