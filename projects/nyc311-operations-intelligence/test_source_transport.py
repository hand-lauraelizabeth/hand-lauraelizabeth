"""Synthetic transport tests; no live request records or network."""
import datetime as dt
from email.message import Message
from io import BytesIO
import json
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request
from source_transport import read_json_with_retries, retry_delay

URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

def failure(code, after=None):
    headers = Message()
    if after is not None:
        headers["Retry-After"] = after
    return HTTPError(URL, code, "Synthetic HTTP error", headers, BytesIO(b""))

class TransportTests(unittest.TestCase):
    def setUp(self):
        self.request = Request(URL)

    def test_rate_limit_then_success_respects_retry_after(self):
        calls, waits = [], []
        def opener(req, timeout):
            calls.append(req)
            if len(calls) == 1:
                raise failure(429, "3")
            return BytesIO(b'[{"total":"2"}]')
        result = read_json_with_retries(self.request, opener=opener, sleeper=waits.append)
        self.assertEqual(result, [{"total": "2"}])
        self.assertEqual((len(calls), waits), (2, [3.0]))

    def test_temporary_http_and_network_failures_bounded(self):
        for problem in (lambda: failure(503), lambda: URLError("temporary")):
            calls, waits = [], []
            def opener(req, timeout):
                calls.append(1)
                raise problem()
            with self.assertRaises((HTTPError, URLError)):
                read_json_with_retries(self.request, opener=opener, sleeper=waits.append)
            self.assertEqual((len(calls), waits), (3, [1.0, 2.0]))

    def test_permanent_http_failure_not_retried(self):
        calls, waits = [], []
        def opener(req, timeout):
            calls.append(1)
            raise failure(403)
        with self.assertRaises(HTTPError):
            read_json_with_retries(self.request, opener=opener, sleeper=waits.append)
        self.assertEqual((len(calls), waits), (1, []))

    def test_long_server_retry_delay_aborts(self):
        waits = []
        def opener(req, timeout):
            raise failure(429, "120")
        with self.assertRaisesRegex(RuntimeError, "exceeds 30-second"):
            read_json_with_retries(self.request, opener=opener, sleeper=waits.append)
        self.assertEqual(waits, [])

    def test_retry_after_http_date_and_invalid_fallback(self):
        now = dt.datetime(2026, 10, 16, 9, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(retry_delay("Fri, 16 Oct 2026 09:00:08 GMT", 0, now=now), 8)
        self.assertEqual(retry_delay("invalid", 1, now=now), 2)

    def test_malformed_response_not_retried(self):
        for body in (b'{"error":"not an array"}', b'not json'):
            calls = []
            def opener(req, timeout):
                calls.append(1)
                return BytesIO(body)
            with self.assertRaises(ValueError):
                read_json_with_retries(self.request, opener=opener,
                                       sleeper=lambda _: self.fail("Unexpected retry"))
            self.assertEqual(len(calls), 1)

    def test_invalid_attempt_budget(self):
        with self.assertRaisesRegex(ValueError, "max_attempts"):
            read_json_with_retries(self.request, max_attempts=4)

if __name__ == "__main__":
    unittest.main()
