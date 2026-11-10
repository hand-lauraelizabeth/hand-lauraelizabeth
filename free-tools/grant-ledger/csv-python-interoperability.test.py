"""Independent Python CSV interoperability gate for synthetic grant ledger exports.

This checks CSV structure and evidence identifiers against Python's standard CSV
reader. It is NOT an Excel, Google Sheets, or assistive-technology test.
"""
import csv
import io
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
JS = r"""
import {calculateLedger, exportTransactionsCSV, exportBudgetCSV, exportJSON} from './core.mjs';
const award={awardId:'AWD-01',awardName:'Fictional award',start:'2026-01-01',end:'2026-12-31'};
const categories=[{categoryId:'CAT-01',label:'Operations, "field"\\nteam',budget:'100.00',restrictionNote:'Fictional only'}];
const expenses=[
 {transactionId:'TX-01',sourceId:' SRC-01 ',date:'2026-02-01',categoryId:'CAT-01',amount:'10.01',percent:'50',allocationBasis:'Timesheet',evidenceRef:'DOC-01',note:'First line\\n"second" line'},
 {transactionId:'TX-02',sourceId:'=1+1',date:'2026-02-02',categoryId:'CAT-01',amount:'0.01',percent:'100',allocationBasis:'',evidenceRef:'DOC-02',note:'Synthetic formula-risk input'},
 {transactionId:'TX-03',sourceId:'＝1+1',date:'2026-02-03',categoryId:'CAT-01',amount:'2.00',percent:'100',allocationBasis:'',evidenceRef:'DOC-03',note:'Fullwidth synthetic formula-risk input'}
];
const result=calculateLedger(award,categories,expenses);
process.stdout.write(JSON.stringify({
 transactions:exportTransactionsCSV(result),
 budget:exportBudgetCSV(result),
 evidence:exportJSON(result)
}));
"""
completed = subprocess.run(
    ["node", "--input-type=module", "-e", JS],
    cwd=HERE, text=True, capture_output=True, check=True, timeout=15,
)
payload = json.loads(completed.stdout)
checks = 0


def verify(condition, label):
    global checks
    assert condition, label
    checks += 1


def read_csv(value):
    return list(csv.DictReader(io.StringIO(value, newline=""), strict=True))


tx = read_csv(payload["transactions"])
budget = read_csv(payload["budget"])
evidence = json.loads(payload["evidence"])
verify(len(tx) == 3, "Three transactions must survive CSV parsing")
verify(len(budget) == 1, "One budget category must survive CSV parsing")
verify([row["transactionId"] for row in tx] == ["TX-01", "TX-02", "TX-03"], "Transaction IDs must preserve order")
verify(tx[0]["sourceId"] == " SRC-01 ", "Exact source ID must preserve spaces")
verify(tx[1]["sourceId"] == "'=1+1", "ASCII formula-like source ID must receive export precaution")
verify(tx[2]["sourceId"] == "'＝1+1", "Fullwidth formula-like source ID must receive export precaution")
verify(tx[0]["note"] == 'First line\\n"second" line', "Embedded newline and quotes must survive CSV")
verify(tx[0]["totalCents"] == "1001", "Cents must be integers in export")
verify(tx[0]["assignedCents"] == "501", "Half-cent allocation must round deterministically")
verify(tx[0]["unassignedCents"] == "500", "Assigned and unassigned must reconcile")
verify(budget[0]["awardId"] == "AWD-01", "Budget export must preserve award ID")
verify(budget[0]["label"] == 'Operations, "field"\\nteam', "Budget label newline/quotes must survive")
verify(budget[0]["actualCents"] == "702", "Assigned total must reconcile")
verify(budget[0]["differenceCents"] == "9298", "Budget difference must reconcile")
verify(evidence["schema"] == "grant-ledger-review-v1", "JSON schema must be explicit")
verify([row["sourceId"] for row in evidence["expenses"]] == [" SRC-01 ", "=1+1", "＝1+1"], "JSON must retain original exact source IDs")
verify(evidence["totalAssignedCents"] == 702, "JSON assigned total must agree with CSV")
verify(evidence["totalUnassignedCents"] == 300, "JSON unassigned total must agree with CSV")
verify(payload["transactions"].endswith("\\r\\n"), "CSV must terminate with CRLF")
verify(all(row["sourceId"] for row in tx), "Every exported row must have source ID")

# A standard-library parse/write/parse cycle must retain the precautionary text.
buffer = io.StringIO(newline="")
writer = csv.DictWriter(buffer, fieldnames=list(tx[0].keys()), lineterminator="\\r\\n")
writer.writeheader()
writer.writerows(tx)
verify(read_csv(buffer.getvalue()) == tx, "Python CSV re-save must preserve values")
print(f"PASS: {checks} independent Python CSV/JSON interoperability assertions")
