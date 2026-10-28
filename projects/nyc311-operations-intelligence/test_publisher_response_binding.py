"""No-network adversarial tests for NYC 311 live response binding."""
from copy import deepcopy
from io import BytesIO
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from publisher_response_binding import (METADATA_URL, MAX_JSON_BYTES,
                                        FETCH_ERROR, HOLD, _official_json,
                                        audit_live_requests)
from aggregate_query_request_gate import ENDPOINT, MONTH, COUNT_SELECT
from aggregate_query_variant_gate import VERIFIED


def url(**params):
    return ENDPOINT + "?" + urlencode({"$" + k: v for k, v in params.items()})


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.urls = {
            "cohort": url(select=COUNT_SELECT, where=MONTH),
            "pairs_primary": url(select="borough,agency,count(*) as n", where=MONTH,
                                 group="borough,agency", order="borough,agency", limit="50000"),
            "pairs_alternate": url(select="borough,agency,count(*) as n", where=MONTH,
                                   group="borough,agency", order="agency,borough", limit="50000", offset="0"),
            "triples_primary": url(select="borough,agency,status,count(*) as n", where=MONTH,
                                   group="borough,agency,status", order="borough,agency,status", limit="50000"),
            "triples_alternate": url(select="borough,agency,status,count(*) as n", where=MONTH,
                                     group="borough,agency,status", order="status,borough,agency", limit="50000", offset="0"),
        }
        self.metadata = {"id": "erm2-nwe9", "publicationStage": "published",
                         "rowIdentifierColumnId": 623546861, "rowsUpdatedAt": 1793151360}
        self.cohort = [{"records": "45", "distinct_keys": "45"}]
        self.pairs = [{"borough": "BRONX", "agency": "A", "n": "30"},
                      {"borough": "QUEENS", "agency": "B", "n": "15"}]
        self.triples = [{"borough": "BRONX", "agency": "A", "status": "Open", "n": "18"},
                        {"borough": "BRONX", "agency": "A", "status": "Closed", "n": "12"},
                        {"borough": "QUEENS", "agency": "B", "status": "Open", "n": "15"}]
        self.calls = []
        self.responses = {METADATA_URL: self.metadata,
                          self.urls["cohort"]: self.cohort,
                          self.urls["pairs_primary"]: self.pairs,
                          self.urls["pairs_alternate"]: deepcopy(self.pairs),
                          self.urls["triples_primary"]: self.triples,
                          self.urls["triples_alternate"]: deepcopy(self.triples)}

    def fetch(self, request):
        self.calls.append(request)
        return deepcopy(self.responses[request])

    def test_valid_synthetic_requests_still_hold(self):
        self.assertEqual(audit_live_requests(self.urls, fetch_json=self.fetch), [HOLD, VERIFIED])
        self.assertEqual(self.calls, [METADATA_URL, *self.urls.values(), METADATA_URL,
                                      self.urls['cohort'], self.urls['pairs_primary'],
                                      self.urls['triples_primary'], METADATA_URL])

    def test_unreviewed_url_rejected_before_network(self):
        self.urls["cohort"] += "&%24where=1%3D1"
        self.assertEqual(audit_live_requests(self.urls, fetch_json=self.fetch), [HOLD, FETCH_ERROR])
        self.assertEqual(self.calls, [])

    def test_incomplete_request_set_rejected_before_network(self):
        del self.urls["pairs_primary"]
        self.assertEqual(audit_live_requests(self.urls, fetch_json=self.fetch), [HOLD, FETCH_ERROR])
        self.assertEqual(self.calls, [])

    def test_cohort_not_singleton_fails(self):
        self.responses[self.urls["cohort"]] = []
        self.assertEqual(audit_live_requests(self.urls, fetch_json=self.fetch), [HOLD, FETCH_ERROR])

    def test_metadata_drift_detected(self):
        n = [0]
        def drifting(request):
            if request == METADATA_URL:
                n[0] += 1
                meta = deepcopy(self.metadata)
                if n[0] == 2:
                    meta["rowsUpdatedAt"] += 1
                return meta
            return self.fetch(request)
        result = audit_live_requests(self.urls, fetch_json=drifting)
        self.assertIn("PUBLISHER_METADATA_CHANGED", result)
        self.assertNotIn(VERIFIED, result)

    def test_status_only_drift_detected(self):
        self.responses[self.urls["triples_alternate"]][0]["n"] = "17"
        self.responses[self.urls["triples_alternate"]][1]["n"] = "13"
        result = audit_live_requests(self.urls, fetch_json=self.fetch)
        self.assertIn("THREE_WAY_QUERY_VARIANTS_DISAGREE", result)
        self.assertNotIn(VERIFIED, result)

    def test_transport_error_redacted(self):
        def fail(_):
            raise OSError("SECRET_UNIQUE_KEY 12345")
        self.assertEqual(audit_live_requests(self.urls, fetch_json=fail), [HOLD, FETCH_ERROR])

    def test_no_source_values_in_failure_codes(self):
        self.responses[self.urls["pairs_primary"]][0]["n"] = "29"
        result = repr(audit_live_requests(self.urls, fetch_json=self.fetch))
        for sensitive in ("BRONX", "QUEENS", "29", "45", "Open"):
            self.assertNotIn(sensitive, result)


    def test_repeat_cohort_drift_fails_closed(self):
        seen = [0]
        def changing(request):
            if request == self.urls["cohort"]:
                seen[0] += 1
                if seen[0] == 2:
                    return [{"records": "46", "distinct_keys": "46"}]
            return self.fetch(request)
        codes = audit_live_requests(self.urls, fetch_json=changing)
        self.assertIn("PUBLISHER_REPEAT_READ_DRIFT", codes)
        self.assertNotIn(VERIFIED, codes)
        self.assertEqual(seen[0], 2)

    def test_repeat_two_way_drift_fails_closed(self):
        seen = [0]
        def changing(request):
            value = self.fetch(request)
            if request == self.urls["pairs_primary"]:
                seen[0] += 1
                if seen[0] == 2:
                    value[0]["n"] = "29"
            return value
        codes = audit_live_requests(self.urls, fetch_json=changing)
        self.assertIn("PUBLISHER_REPEAT_READ_DRIFT", codes)
        self.assertNotIn(VERIFIED, codes)

    def test_repeat_three_way_status_drift_fails_closed(self):
        seen = [0]
        def changing(request):
            value = self.fetch(request)
            if request == self.urls["triples_primary"]:
                seen[0] += 1
                if seen[0] == 2:
                    value[0]["n"], value[1]["n"] = "17", "13"
            return value
        codes = audit_live_requests(self.urls, fetch_json=changing)
        self.assertIn("PUBLISHER_REPEAT_READ_DRIFT", codes)
        self.assertNotIn(VERIFIED, codes)

    def test_final_metadata_drift_fails_closed(self):
        seen = [0]
        def changing(request):
            value = self.fetch(request)
            if request == METADATA_URL:
                seen[0] += 1
                if seen[0] == 3:
                    value["rowsUpdatedAt"] += 1
            return value
        codes = audit_live_requests(self.urls, fetch_json=changing)
        self.assertIn("PUBLISHER_REPEAT_READ_DRIFT", codes)
        self.assertNotIn(VERIFIED, codes)
        self.assertEqual(seen[0], 3)

    def test_repeat_transport_failure_redacted(self):
        seen = [0]
        def changing(request):
            if request == self.urls["cohort"]:
                seen[0] += 1
                if seen[0] == 2:
                    raise OSError("PRIVATE_RECORD 12345")
            return self.fetch(request)
        self.assertEqual(audit_live_requests(self.urls, fetch_json=changing),
                         [HOLD, FETCH_ERROR])

    def test_repeat_source_values_never_exposed(self):
        seen = [0]
        def changing(request):
            value = self.fetch(request)
            if request == self.urls["pairs_primary"]:
                seen[0] += 1
                if seen[0] == 2:
                    value[0]["n"] = "29"
            return value
        result = repr(audit_live_requests(self.urls, fetch_json=changing))
        self.assertIn("PUBLISHER_REPEAT_READ_DRIFT", result)
        for sensitive in ("BRONX", "QUEENS", "29", "45", "Open"):
            self.assertNotIn(sensitive, result)



class FakeResponse:
    def __init__(self, url, data=b'[]', status=200, content_type='application/json'):
        self._url = url
        self._data = BytesIO(data)
        self.status = status
        self.headers = {"Content-Type": content_type}
    def geturl(self):
        return self._url
    def read(self, n=-1):
        return self._data.read(n)
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass


class HTTPTests(unittest.TestCase):
    TARGET = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
    def check(self, response):
        class FakeOpener:
            def open(self, *_args, **_kwargs):
                return response
        with patch('publisher_response_binding.build_opener', return_value=FakeOpener()):
            return _official_json(self.TARGET)

    def test_http_200_json(self):
        self.assertEqual(self.check(FakeResponse(self.TARGET)), [])

    def test_http_redirect_destination_rejected(self):
        with self.assertRaises(ValueError):
            self.check(FakeResponse("https://evil.example/data"))

    def test_http_non_200_rejected(self):
        with self.assertRaises(ValueError):
            self.check(FakeResponse(self.TARGET, status=206))

    def test_http_html_rejected(self):
        with self.assertRaises(ValueError):
            self.check(FakeResponse(self.TARGET, content_type="text/html"))

    def test_http_oversize_rejected(self):
        with self.assertRaises(ValueError):
            self.check(FakeResponse(self.TARGET, data=b'x' * (MAX_JSON_BYTES + 1)))

    def test_http_malformed_json_rejected(self):
        with self.assertRaises(ValueError):
            self.check(FakeResponse(self.TARGET, data=b'not json'))


if __name__ == '__main__':
    unittest.main()
