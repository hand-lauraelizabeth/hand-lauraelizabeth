import assert from 'node:assert/strict';
import {exportFindingsCSV} from './report-export.mjs';

let checks=0;
const row={id:'F-001',rule:'image-alt-missing',severity:'review',location:'img#safe',
 message:'Review "quoted", comma, and provenance',reference:'WCAG 1.1.1'};
const safe=exportFindingsCSV([row]);
assert.ok(safe.startsWith('id,rule,severity,location,message,reference\r\n'));checks++;
assert.ok(safe.includes('"Review ""quoted"", comma, and provenance"'));checks++;
assert.ok(safe.includes('"F-001"'));checks++;
assert.equal(exportFindingsCSV([]).split('\r\n').length,2);checks++;
const original=JSON.stringify(row);
for(const risky of [
 '=1+1',' +SUM(A1:A2)','-3','@cmd','\u202eleft','abc\u200bhidden',
 '\u2066isolate','\ufeff=SUM(A1:A2)','hello\nworld','hello\tworld',
 'hello\u0000world','abc\u007fdef','abc\u009fdef','abc\u200fdef',
 'abc\u2069def','\u00a0=2+2','\uFF1D1+1','\uFF0B3','\uFF0D2','\uFF20cmd'
]){
 const candidate={...row,location:risky};
 assert.throws(()=>exportFindingsCSV([candidate]),/CSV export blocked: unsafe spreadsheet cell in location \(finding 1\)/);
 checks++;
 assert.equal(JSON.parse(JSON.stringify(candidate)).location,risky);checks++;
}
assert.equal(JSON.stringify(row),original);checks++;
console.log('PASS: '+checks+' FT-10 exact-source CSV safety and JSON-fidelity assertions');
