"""Independent standard-library CSV import of synthetic FT-05 export."""
import csv
import io
import sys

raw = sys.stdin.read()
assert raw.startswith('sourceId,date,claim,status,kind,group\r\n')
assert raw.endswith('\r\n')
assert raw.count('\r\n') == 3  # header + two records, not the quoted LF
rows = list(csv.DictReader(io.StringIO(raw, newline=''), strict=True))
assert len(rows) == 2
assert list(rows[0]) == ['sourceId', 'date', 'claim', 'status', 'kind', 'group']
assert rows[0]['sourceId'] == 'cafe\u0301'
assert rows[0]['claim'] == "'＋SUM(1,2)"
assert rows[0]['status'] == 'disputed'
assert rows[0]['kind'] == 'inference'
assert rows[0]['group'] == ''
assert rows[1]['sourceId'] == ' ID, "one" '
assert rows[1]['claim'] == 'Line one\nLine two'
assert rows[1]['group'] == "'＝group"
assert rows[1]['status'] == 'reported'
assert rows[1]['kind'] == 'source'
assert len(set(r['sourceId'] for r in rows)) == 2
print('PASS: 16 Python CSV import assertions')
