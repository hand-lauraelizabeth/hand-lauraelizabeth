"""Independently parse and validate the FT-04 exported CSV using Python's csv module.
This is NOT the same as reopening the file in Excel/Google Sheets.
"""
import csv
import io
import sys
from decimal import Decimal

source = sys.stdin.read()
assert source.endswith("\r\n"), "Expected CRLF CSV record termination"
headers = ["Date", "Change (USD)", "End-of-day balance (USD)", "Event IDs", "Event labels"]
reader = csv.DictReader(io.StringIO(source, newline=""))
assert reader.fieldnames == headers, (reader.fieldnames, headers)
records = list(reader)
assert len(records) == 10, f"CSV record count {len(records)} differs from 10"
assert all(None not in row for row in records), "Extra comma created unexpected cell"
assert all(None not in row.values() for row in records), "Missing column due to quoting"
balance = Decimal("10000.00")
for i, row in enumerate(records):
    assert row["Date"] == f"2026-10-{14 + i}", ("date", i, row["Date"])
    expected_change = Decimal("-123.45" if i % 2 == 0 else "100.01")
    change = Decimal(row["Change (USD)"])
    assert change == expected_change, ("change", i, change)
    balance += change
    assert Decimal(row["End-of-day balance (USD)"]) == balance, (
        "balance", i, row["End-of-day balance (USD)"]
    )
assert balance == Decimal("9882.80"), balance
assert records[0]["Event IDs"] == "'=unsafe-id"
assert records[0]["Event labels"].startswith("'=HYPERLINK(")
assert records[1]["Event labels"].startswith("'+SUM(")
assert records[2]["Event labels"].startswith("'-cmd")
assert records[3]["Event labels"].startswith("'@SUM(")
assert records[4]["Event labels"].startswith("'\t=1+1")
assert records[5]["Event labels"].startswith("'   =SUM")
assert records[6]["Event labels"].startswith("'\r\n=2+2")
assert records[7]["Event labels"] == 'Quoted "value", comma'
assert records[8]["Event labels"] == "Multiline\nstatement"
assert records[9]["Event labels"] == "Résumé — ñ and €"
print("FT-04 CSV independent Python import: PASS — 10 rows, Decimal balance, 7 formula-style labels, commas, double quotes, CRLF and Unicode")
print("Manual CSV reopening in Excel and Google Sheets remains unverified.")
