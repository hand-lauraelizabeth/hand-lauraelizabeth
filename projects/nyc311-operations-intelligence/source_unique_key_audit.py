"""Private streaming NYC 311 CSV unique-key audit; never authenticates source origin.

Only redacted status codes leave this module. Source bytes, keys and row data
remain local. The caller must separately authenticate the export's provenance,
query parameters, date window and as-of cutoff.
"""
import csv
from datetime import datetime
import re
import sqlite3
import tempfile
from pathlib import Path

MAX_CSV_FIELD = 1024 * 1024
MAX_COLUMNS = 512
MAX_KEY_LENGTH = 256


def _floating_created_date(value):
    """Parse source-local floating timestamps without guessing a timezone."""
    if not value or value != value.strip():
        raise ValueError('empty or padded created_date')
    if len(value) >= 19 and value[4:5] == '-' and value[10:11] in ('T', ' '):
        result = datetime.fromisoformat(value)
    else:
        for fmt in ('%m/%d/%Y %I:%M:%S %p', '%m/%d/%Y %I:%M:%S.%f %p',
                    '%m/%d/%Y %H:%M:%S'):
            try:
                result = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError('unrecognized floating timestamp')
    if result.tzinfo is not None:
        raise ValueError('timezone-bearing value is not a floating timestamp')
    return result


def audit_unique_keys(source_csv, *, expected_rows=None, expected_month=None):
    """Return redacted, fail-closed audit codes for one source CSV.

    expected_rows must be a nonnegative integer if supplied. This audits
    source-file grain, not publisher completeness or cross-snapshot stability.
    expected_month, when supplied, is YYYY-MM in source-local floating time.
    """
    if expected_rows is not None and (type(expected_rows) is not int or expected_rows < 0):
        return ['SOURCE_ROW_COUNT_CONTRACT_INVALID']
    if expected_month is not None and (type(expected_month) is not str or
            re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', expected_month) is None):
        return ['SOURCE_CREATED_MONTH_CONTRACT_INVALID']
    old_limit = csv.field_size_limit()
    try:
        csv.field_size_limit(MAX_CSV_FIELD)
        with tempfile.TemporaryDirectory(prefix='nyc311_keys_') as tmp:
            with sqlite3.connect(str(Path(tmp) / 'keys.sqlite')) as db:
                db.execute('CREATE TABLE keys (value TEXT PRIMARY KEY) WITHOUT ROWID')
                with Path(source_csv).open('r', encoding='utf-8-sig', newline='') as handle:
                    reader = csv.reader(handle, strict=True)
                    try:
                        header = next(reader)
                    except StopIteration:
                        return ['SOURCE_CSV_HEADER_INVALID']
                    if not header or len(header) > MAX_COLUMNS:
                        return ['SOURCE_CSV_HEADER_INVALID']
                    normalized = [h.strip().lower().replace(' ', '_') for h in header]
                    if any(not h for h in normalized) or len(set(normalized)) != len(normalized):
                        return ['SOURCE_CSV_HEADER_INVALID']
                    if normalized.count('unique_key') != 1:
                        return ['SOURCE_UNIQUE_KEY_COLUMN_MISSING']
                    index = normalized.index('unique_key')
                    if expected_month is not None and 'created_date' not in normalized:
                        return ['SOURCE_CREATED_DATE_COLUMN_MISSING']
                    date_index = (normalized.index('created_date')
                                  if expected_month is not None else None)
                    rows = 0
                    for row in reader:
                        if len(row) != len(header):
                            return ['SOURCE_CSV_ROW_STRUCTURE_INVALID']
                        if date_index is not None:
                            try:
                                created = _floating_created_date(row[date_index])
                            except ValueError:
                                return ['SOURCE_CREATED_DATE_INVALID']
                            if created.strftime('%Y-%m') != expected_month:
                                return ['SOURCE_CREATED_DATE_OUTSIDE_MONTH']
                        key = row[index]
                        # Official NYC Open Data declares Unique Key as TEXT,
                        # not a numeric type. Preserve leading zeroes and Unicode.
                        if (not key or len(key) > MAX_KEY_LENGTH or
                                any(ord(ch) < 32 or ord(ch) == 127 for ch in key)):
                            return ['SOURCE_UNIQUE_KEY_INVALID']
                        try:
                            db.execute('INSERT INTO keys(value) VALUES (?)', (key,))
                        except sqlite3.IntegrityError:
                            return ['SOURCE_UNIQUE_KEY_DUPLICATE']
                        rows += 1
                    if rows == 0:
                        return ['SOURCE_CSV_NO_DATA_ROWS']
                    if expected_rows is not None and rows != expected_rows:
                        return ['SOURCE_ROW_COUNT_MISMATCH']
                    codes = ['SOURCE_UNIQUE_KEYS_DISTINCT']
                    codes.append('SOURCE_ROW_COUNT_MATCHED' if expected_rows is not None
                                 else 'SOURCE_ROW_COUNT_NOT_BOUND')
                    codes.append('SOURCE_CREATED_DATE_MONTH_MATCHED' if expected_month is not None
                                 else 'SOURCE_CREATED_DATE_MONTH_NOT_BOUND')
                    return codes
    except (OSError, UnicodeError, csv.Error, sqlite3.Error, ValueError, OverflowError):
        return ['SOURCE_UNIQUE_KEY_AUDIT_FAILED_CLOSED']
    finally:
        csv.field_size_limit(old_limit)
