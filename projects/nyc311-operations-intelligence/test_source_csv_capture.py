"""Offline transport-adversarial tests. No official CSV or network access."""
from datetime import datetime, timezone
from hashlib import sha256
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json

from source_export_query_contract import canonical_export_url, query_fingerprint
from source_csv_capture import capture_official_csv, CaptureError, main

URL = canonical_export_url(limit=400000)
BODY = (b'unique_key,created_date,closed_date,agency,borough,complaint_type,status\n'
        b'0001,2026-09-01T00:00:00,,ABC,Bronx,Example,Open\n')


class Response(io.BytesIO):
    def __init__(self, data=BODY, *, url=URL, status=200, headers=None):
        super().__init__(data)
        self.url = url
        self.status = status
        self.headers = headers if headers is not None else {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Length': str(len(data)),
        }

    def geturl(self):
        return self.url


class Opener:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def open(self, request, timeout):
        self.calls += 1
        assert request.full_url == URL
        assert request.get_header('Accept-encoding') == 'identity'
        assert timeout == 60
        return self.response


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'private.csv'

    def run_capture(self, response=None, **kwargs):
        opener = Opener(response if response is not None else Response())
        return capture_official_csv(URL, self.path, reference_rows=323630,
                                    opener=opener, **({"max_bytes": 1024} | kwargs))

    def fails(self, code, response=None, **kwargs):
        with self.assertRaises(CaptureError) as ctx:
            self.run_capture(response, **kwargs)
        self.assertEqual(str(ctx.exception), code)
        self.assertFalse(self.path.exists())
        self.assertFalse(list(self.path.parent.glob('.nyc311_capture_*')))

    def test_exact_capture_receipt_and_private_bytes(self):
        result = self.run_capture(clock=lambda: datetime(2026, 10, 24, 9, 0,
                                                         tzinfo=timezone.utc))
        self.assertEqual(self.path.read_bytes(), BODY)
        self.assertEqual(result['source_sha256'], sha256(BODY).hexdigest())
        self.assertEqual(result['source_query_sha256'], query_fingerprint(URL))
        self.assertEqual(result['source_bytes'], len(BODY))
        self.assertEqual(result['captured_at_utc'], '2026-10-24T09:00:00+00:00')
        self.assertFalse(result['source_origin_authenticated'])
        self.assertEqual(result['status'], 'HOLD')
        self.assertFalse(list(self.path.parent.glob('.nyc311_capture_*')))

    def test_redirect_target_rejected(self):
        self.fails('SOURCE_HTTP_REDIRECT_OR_URL_MISMATCH',
                   Response(url='https://other.example/311.csv'))

    def test_non_200_rejected(self):
        self.fails('SOURCE_HTTP_STATUS_INVALID', Response(status=206))

    def test_html_masquerade_rejected(self):
        self.fails('SOURCE_HTTP_CONTENT_TYPE_INVALID',
                   Response(headers={'Content-Type': 'text/html'}))

    def test_gzip_body_rejected(self):
        self.fails('SOURCE_HTTP_ENCODING_INVALID',
                   Response(headers={'Content-Type': 'text/csv',
                                     'Content-Encoding': 'gzip'}))

    def test_oversized_declared_body_rejected(self):
        self.fails('SOURCE_CAPTURE_SIZE_LIMIT_EXCEEDED',
                   Response(headers={'Content-Type': 'text/csv',
                                     'Content-Length': '999999'}))

    def test_oversized_stream_rejected_and_cleaned(self):
        self.fails('SOURCE_CAPTURE_SIZE_LIMIT_EXCEEDED',
                   Response(data=b'X' * 200), max_bytes=100)

    def test_truncated_body_rejected_and_cleaned(self):
        self.fails('SOURCE_HTTP_LENGTH_MISMATCH',
                   Response(headers={'Content-Type': 'text/csv',
                                     'Content-Length': str(len(BODY) + 1)}))

    def test_empty_body_rejected(self):
        self.fails('SOURCE_HTTP_LENGTH_MISMATCH', Response(data=b''))

    def test_existing_destination_preserved(self):
        self.path.write_bytes(b'original')
        with self.assertRaisesRegex(CaptureError, 'SOURCE_DESTINATION_EXISTS'):
            self.run_capture()
        self.assertEqual(self.path.read_bytes(), b'original')

    def test_bad_query_rejected_before_open(self):
        opener = Opener(Response())
        with self.assertRaisesRegex(CaptureError, 'SOURCE_QUERY_NOT_VERIFIED'):
            capture_official_csv(URL + '&$offset=1', self.path,
                                 reference_rows=323630, opener=opener)
        self.assertEqual(opener.calls, 0)

    def test_bad_content_length_rejected(self):
        self.fails('SOURCE_HTTP_LENGTH_INVALID',
                   Response(headers={'Content-Type': 'text/csv',
                                     'Content-Length': '-1'}))

    def test_invalid_limit_rejected(self):
        self.fails('SOURCE_CAPTURE_LIMIT_INVALID', max_bytes=0)

    def test_invalid_clock_does_not_publish_destination(self):
        self.fails('SOURCE_CAPTURE_CLOCK_INVALID', clock=lambda: datetime(2026, 10, 24))

    def test_query_fingerprint_failure_never_publishes_csv(self):
        # Regression: metadata used to be assembled AFTER os.link, leaving
        # an orphan CSV when query_fingerprint raised.
        with patch('source_csv_capture.query_fingerprint',
                   side_effect=ValueError('synthetic fingerprint error')):
            self.fails('SOURCE_HTTP_OR_DISK_FAILED_CLOSED')

    def test_timestamp_serialization_failure_never_publishes_csv(self):
        class BadTimezone(datetime):
            def astimezone(self, tz=None):
                raise ValueError('synthetic timestamp conversion error')

        self.fails('SOURCE_HTTP_OR_DISK_FAILED_CLOSED',
                   clock=lambda: BadTimezone(2026, 10, 24, 9, 0,
                                             tzinfo=timezone.utc))

    def test_competing_source_creation_never_overwritten(self):
        def race_link(src, dst):
            self.path.write_bytes(b'other process')
            raise FileExistsError('synthetic concurrent source creation')

        with patch('source_csv_capture.os.link', side_effect=race_link):
            with self.assertRaisesRegex(CaptureError, 'SOURCE_HTTP_OR_DISK_FAILED_CLOSED'):
                self.run_capture()
        self.assertEqual(self.path.read_bytes(), b'other process')
        self.assertFalse(list(self.path.parent.glob('.nyc311_capture_*')))

    def test_main_saves_receipt_but_remains_hold(self):
        receipt = self.path.parent / 'receipt.json'
        with patch('source_csv_capture.capture_official_csv',
                   return_value={'status': 'HOLD', 'source_bytes': 120}) as capture:
            rc = main(['--source-csv', str(self.path), '--receipt-json', str(receipt),
                       '--reference-rows', '323630', '--limit', '400000'])
        self.assertEqual(rc, 2)
        self.assertEqual(json.loads(receipt.read_text())['status'], 'HOLD')
        self.assertEqual(capture.call_args.kwargs['reference_rows'], 323630)

    def test_main_refuses_existing_receipt_without_capture(self):
        receipt = self.path.parent / 'receipt.json'
        receipt.write_bytes(b'original')
        with patch('source_csv_capture.capture_official_csv') as capture:
            rc = main(['--source-csv', str(self.path), '--receipt-json', str(receipt),
                       '--reference-rows', '323630'])
        self.assertEqual(rc, 2)
        capture.assert_not_called()
        self.assertEqual(receipt.read_bytes(), b'original')

    def test_missing_length_stream_is_bounded_and_accepted(self):
        result = self.run_capture(Response(headers={'Content-Type': 'text/csv'}))
        self.assertIsNone(result['http_content_length'])
        self.assertEqual(result['source_bytes'], len(BODY))


    def test_main_receipt_serialization_failure_cleans_new_csv_and_stage(self):
        receipt = self.path.parent / 'receipt.json'
        def captured(*args, **kwargs):
            self.path.write_bytes(BODY)
            return {'status': 'HOLD', 'source_bytes': len(BODY)}
        with patch('source_csv_capture.capture_official_csv', side_effect=captured):
            with patch('source_csv_capture.json.dump', side_effect=OSError('disk full')):
                rc = main(['--source-csv', str(self.path),
                           '--receipt-json', str(receipt),
                           '--reference-rows', '323630'])
        self.assertEqual(rc, 2)
        self.assertFalse(self.path.exists())
        self.assertFalse(receipt.exists())
        self.assertFalse(list(self.path.parent.glob('.nyc311_receipt_*')))

    def test_main_receipt_race_preserves_existing_receipt_and_cleans_csv(self):
        receipt = self.path.parent / 'receipt.json'
        def captured(*args, **kwargs):
            self.path.write_bytes(BODY)
            receipt.write_text('other process', encoding='utf-8')
            return {'status': 'HOLD', 'source_bytes': len(BODY)}
        with patch('source_csv_capture.capture_official_csv', side_effect=captured):
            rc = main(['--source-csv', str(self.path),
                       '--receipt-json', str(receipt),
                       '--reference-rows', '323630'])
        self.assertEqual(rc, 2)
        self.assertFalse(self.path.exists())
        self.assertEqual(receipt.read_text(), 'other process')
        self.assertFalse(list(self.path.parent.glob('.nyc311_receipt_*')))

    def test_main_capture_failure_never_creates_receipt(self):
        receipt = self.path.parent / 'receipt.json'
        with patch('source_csv_capture.capture_official_csv',
                   side_effect=CaptureError('SOURCE_HTTP_STATUS_INVALID')):
            rc = main(['--source-csv', str(self.path),
                       '--receipt-json', str(receipt),
                       '--reference-rows', '323630'])
        self.assertEqual(rc, 2)
        self.assertFalse(self.path.exists())
        self.assertFalse(receipt.exists())
        self.assertFalse(list(self.path.parent.glob('.nyc311_receipt_*')))

    def test_main_success_removes_staged_receipt(self):
        receipt = self.path.parent / 'receipt.json'
        def captured(*args, **kwargs):
            self.path.write_bytes(BODY)
            return {'status': 'HOLD', 'source_bytes': len(BODY)}
        with patch('source_csv_capture.capture_official_csv', side_effect=captured):
            rc = main(['--source-csv', str(self.path),
                       '--receipt-json', str(receipt),
                       '--reference-rows', '323630'])
        self.assertEqual(rc, 2)
        self.assertEqual(self.path.read_bytes(), BODY)
        self.assertEqual(json.loads(receipt.read_text())['source_bytes'], len(BODY))
        self.assertFalse(list(self.path.parent.glob('.nyc311_receipt_*')))


if __name__ == '__main__':
    unittest.main()
