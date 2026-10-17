"""Cross-language CSV/JSON checks with fictional records; not a spreadsheet-app test."""
import csv
import io
import json
import subprocess
from pathlib import Path

js = """
import {calculateLedger, exportTransactionsCSV, exportBudgetCSV, exportJSON} from './core.mjs';
const result = calculateLedger(
 {awardId:'AWD-01',awardName:'Fictional',start:'2026-01-01',end:'2026-12-31'},
 [{categoryId:'C-1',label:'Two, columns',budget:'100.00',restrictionNote:''}],
 [{transactionId:'TX-1',sourceId:' SRC-01 ',date:'2026-02-01',categoryId:'C-1',amount:'10.01',percent:'50',allocationBasis:'Timesheet',evidenceRef:'DOC-1',note:'Quoted "value"'},
  {transactionId:'TX-2',sourceId:'=1+1',date:'2026-02-02',categoryId:'C-1',amount:'2.00',percent:'100',allocationBasis:'',evidenceRef:'DOC-2',note:'Fictional risk'}]
);
process.stdout.write(JSON.stringify({transactions:exportTransactionsCSV(result),budget:exportBudgetCSV(result),json:exportJSON(result)}));
"""
run = subprocess.run(["node", "--input-type=module", "-e", js],
                     cwd=Path(__file__).parent, text=True, capture_output=True,
                     check=True, timeout=15)
data = json.loads(run.stdout)
def read_csv(text):
    return list(csv.DictReader(io.StringIO(text, newline=""), strict=True))
rows = read_csv(data["transactions"])
budget = read_csv(data["budget"])
evidence = json.loads(data["json"])
assert len(rows) == 2
assert rows[0]["transactionId"] == "TX-1"
assert rows[0]["sourceId"] == " SRC-01 "
assert rows[1]["sourceId"] == "'=1+1"
assert rows[0]["note"] == 'Quoted "value"'
assert rows[0]["assignedCents"] == "501"
assert rows[0]["unassignedCents"] == "500"
assert rows[1]["assignedCents"] == "200"
assert len(budget) == 1
assert budget[0]["label"] == "Two, columns"
assert budget[0]["actualCents"] == "701"
assert budget[0]["differenceCents"] == "9299"
assert evidence["schema"] == "grant-ledger-review-v1"
assert evidence["expenses"][1]["sourceId"] == "=1+1"
assert evidence["totalAssignedCents"] == 701
assert data["transactions"].endswith(chr(13)+chr(10))
print("PASS: 16 independent Python CSV/JSON assertions")
