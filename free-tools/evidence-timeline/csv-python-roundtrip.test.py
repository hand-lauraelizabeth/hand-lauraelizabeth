"""Independent CSV byte-level round-trip with Python's CSV reader.

Synthetic records only. This checks interoperability with a second CSV parser,
not Excel/Sheets behavior or spreadsheet-formula execution.
"""
import csv
import io
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
js = r'''
import {exportEvidenceCSV} from './core.mjs';
const records = [
 {sourceId:' ID ', date:'2026-10-15', claim:'A "quoted" line\nand Ω café',status:'reported',kind:'source',group:' G '},
 {sourceId:'B', date:'2026-10-16', claim:'=1+2',status:'disputed',kind:'observation',group:''},
 {sourceId:'C', date:'2026-10-17', claim:'＋3',status:'unresolved',kind:'inference',group:''},
];
process.stdout.write(exportEvidenceCSV(records));
'''
run = subprocess.run(['node', '--input-type=module', '-e', js], cwd=HERE, capture_output=True, check=True)
raw = run.stdout
checks = 0
def ok(condition, description):
    global checks
    assert condition, description
    checks += 1
ok(raw.endswith(b'\r\n'), 'CRLF final record delimiter')
ok(raw.count(b'\r\n') == 4, 'exact CRLF record delimiters; embedded newline preserved')
ok(b'\xef\xbb\xbf' not in raw, 'no injected UTF-8 BOM')
text = raw.decode('utf-8', errors='strict')
rows = list(csv.reader(io.StringIO(text, newline=''), strict=True))
ok(len(rows) == 4, 'header plus three records')
ok(rows[0] == ['sourceId','date','claim','status','kind','group'], 'schema preserved')
ok(all(len(row) == 6 for row in rows), 'rectangular records')
ok(rows[1][0] == ' ID ', 'exact identifier whitespace preserved')
ok(rows[1][2] == 'A "quoted" line\nand Ω café', 'multiline quotes and Unicode round-trip')
ok(rows[1][5] == ' G ', 'group whitespace preserved')
ok(rows[2][2] == "'=1+2", 'ASCII formula prefix mitigated')
ok(rows[3][2] == "'＋3", 'full-width formula prefix mitigated')
ok(rows[2][3:5] == ['disputed','observation'], 'classifications preserved')
ok(rows[3][3:5] == ['unresolved','inference'], 'third row classifications preserved')
ok(rows[3][5] == '', 'empty group preserved')
print(f'{checks} synthetic cross-parser CSV assertions PASS (Python csv + Node export)')
