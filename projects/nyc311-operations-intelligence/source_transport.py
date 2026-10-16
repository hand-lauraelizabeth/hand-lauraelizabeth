"""Bounded JSON request retries for a read-only public-data export."""
import datetime as dt
from email.utils import parsedate_to_datetime
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

RETRYABLE_HTTP = frozenset({429, 500, 502, 503, 504})

def retry_delay(header, attempt, *, now=None):
    delay = float(2 ** attempt)
    if header is not None:
        value = str(header).strip()
        if value.isascii() and value.isdecimal():
            seconds = int(value)
            if seconds > 30:
                raise RuntimeError("Server Retry-After exceeds 30-second request budget")
            delay = float(seconds)
        else:
            try:
                at = parsedate_to_datetime(value)
                if at.tzinfo is None:
                    raise ValueError("Missing timezone")
                current = now if now is not None else dt.datetime.now(dt.timezone.utc)
                delay = max(0.0, (at - current).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass
    if delay > 30:
        raise RuntimeError("Server Retry-After exceeds 30-second request budget")
    return delay

def read_json_with_retries(request, *, opener=urlopen, sleeper=time.sleep, max_attempts=3, now=None):
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        raise ValueError("max_attempts must be 1..3")
    for attempt in range(max_attempts):
        try:
            with opener(request, timeout=45) as response:
                data = json.load(response)
            if not isinstance(data, list):
                raise ValueError("Expected a source JSON array")
            return data
        except HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP or attempt == max_attempts - 1:
                raise
            try:
                delay = retry_delay(exc.headers.get("Retry-After"), attempt, now=now)
            finally:
                exc.close()
        except URLError:
            if attempt == max_attempts - 1:
                raise
            delay = retry_delay(None, attempt, now=now)
        sleeper(delay)
    raise AssertionError("Unreachable retry state")
