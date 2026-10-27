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
import stat
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
        # Publishing is not complete until the staging hard link is removed.
        # If that cleanup fails, roll back only our own inode; never delete a
        # competing file that may have replaced the destination in the meantime.
        try:
            temporary.unlink()
        except OSError as exc:
            try:
                if target.samefile(temporary):
                    target.unlink()
            except OSError:
                pass
            raise CaptureError('SOURCE_CAPTURE_CLEANUP_FAILED') from exc
        temporary = None
        return metadata
    except CaptureError:
        raise
    except (OSError, ValueError, TypeError, HTTPException) as exc:
        raise CaptureError('SOURCE_HTTP_OR_DISK_FAILED_CLOSED') from exc
    finally:
        if temporary is not None:
            # Best effort after a failed capture or rollback. An unlink failure
            # here must not mask the original fail-closed error.
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass



def _source_path_still_pinned(source, source_fd, source_inode):
    """Ensure the CSV pathname still resolves to the verified regular file.

    This detects replacement and symlink swaps during receipt staging. It
    cannot make two separate filesystem paths a single atomic transaction;
    the independent downstream source SHA-256 audit remains mandatory.
    """
    if source_fd is None:
        return True  # Offline injected capture mocks may not create a file.
    try:
        current = source.lstat()
        held = os.fstat(source_fd)
    except OSError:
        return False
    return (stat.S_ISREG(current.st_mode) and
            stat.S_ISREG(held.st_mode) and
            (current.st_dev, current.st_ino) == source_inode and
            (held.st_dev, held.st_ino) == source_inode)


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
    source_inode = None
    source_fd = None  # Pin our inode so unlink/recreate cannot reuse its number.
    receipt_committed = False
    staged_receipt = None
    try:
        metadata = capture_official_csv(
            canonical_export_url(limit=args.limit), source,
            reference_rows=args.reference_rows)
        source_created = True
        # Snapshot the inode before receipt operations. A competing process may
        # replace this pathname; rollback must never delete its replacement.
        try:
            # Keep a descriptor open through receipt serialization and rollback.
            # A bare (device, inode) snapshot is insufficient: after unlink,
            # a competing replacement can reuse the released inode number.
            source_fd = os.open(source, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
            source_stat = os.fstat(source_fd)
            # Bind the receipt to the bytes on the descriptor we actually hold.
            # A pathname can be replaced between capture() returning and open().
            # On mismatch do not record an inode for rollback: it may belong to
            # a competing writer, and preserving it is safer than deleting it.
            if isinstance(metadata, dict) and 'source_sha256' in metadata:
                expected_hash = metadata['source_sha256']
                expected_bytes = metadata.get('source_bytes')
                if (not isinstance(expected_hash, str) or len(expected_hash) != 64 or
                        any(c not in '0123456789abcdef' for c in expected_hash) or
                        type(expected_bytes) is not int or expected_bytes < 1 or
                        not stat.S_ISREG(source_stat.st_mode) or
                        source_stat.st_size != expected_bytes):
                    raise CaptureError('SOURCE_RECEIPT_BYTE_BINDING_INVALID')
                digest = sha256()
                while True:
                    chunk = os.read(source_fd, CHUNK_BYTES)
                    if not chunk:
                        break
                    digest.update(chunk)
                if (digest.hexdigest() != expected_hash or
                        os.fstat(source_fd).st_size != expected_bytes):
                    raise CaptureError('SOURCE_RECEIPT_BYTE_BINDING_MISMATCH')
            source_inode = (source_stat.st_dev, source_stat.st_ino)
        except FileNotFoundError:
            # Preserve compatibility with injectable offline capture mocks.
            # Real capture always creates a source; no inode means no deletion.
            pass
        with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=receipt.parent,
                prefix='.nyc311_receipt_', suffix='.tmp', delete=False) as handle:
            staged_receipt = Path(handle.name)
            json.dump(metadata, handle, indent=2, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        # A competitor can replace the pathname after the initial digest,
        # including while JSON is being serialized. Do not bind a receipt to
        # the old descriptor if the visible source path now names another file.
        if not _source_path_still_pinned(source, source_fd, source_inode):
            raise CaptureError('SOURCE_PATH_CHANGED_BEFORE_RECEIPT')
        os.link(staged_receipt, receipt)  # atomic, exclusive, no clobber
        # Recheck after the link as well; a swap during link must not leave
        # an apparently valid receipt. The exception handler removes only
        # the receipt hard link belonging to our staged inode.
        if not _source_path_still_pinned(source, source_fd, source_inode):
            raise CaptureError('SOURCE_PATH_CHANGED_DURING_RECEIPT')
        # The receipt is not committed until its staging link is removed.
        # Otherwise a cleanup error can escape after both outputs exist.
        try:
            staged_receipt.unlink()
        except OSError as exc:
            # Only remove the receipt if it still names our staged inode.
            # A competing replacement must remain untouched.
            try:
                if receipt.samefile(staged_receipt):
                    receipt.unlink()
            except OSError:
                pass
            raise CaptureError('SOURCE_RECEIPT_CLEANUP_FAILED') from exc
        staged_receipt = None
        receipt_committed = True
    except (CaptureError, ValueError, OSError, TypeError):
        # The exclusive receipt link may already exist if a source swap
        # occurred during os.link(). Remove only our own staged inode;
        # preserve any competing receipt written at the same pathname.
        if staged_receipt is not None:
            try:
                if receipt.samefile(staged_receipt):
                    receipt.unlink()
            except OSError:
                pass
        if source_created and not receipt_committed and source_inode is not None:
            # Roll back only the source inode captured by this process. If the
            # path has been replaced, retain the competing file unmodified.
            try:
                current = source.lstat()
                if (current.st_dev, current.st_ino) == source_inode:
                    source.unlink()
            except OSError:
                # Cleanup failure must not mask the original HOLD condition.
                pass
        print('HOLD: source capture or receipt failed closed')
        return 2
    finally:
        if source_fd is not None:
            try:
                os.close(source_fd)
            except OSError:
                pass  # Never mask the original HOLD or successful receipt result.
        if staged_receipt is not None:
            # Best effort: cleanup must not mask the original HOLD failure.
            try:
                staged_receipt.unlink(missing_ok=True)
            except OSError:
                pass
    print('HOLD: private source captured; provenance, row and disclosure QA required')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
