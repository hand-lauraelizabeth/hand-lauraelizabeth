/* Synthetic cross-implementation CSV/TSV interoperability oracle.
 * Python's independent csv.reader/csv.writer is NOT Excel/Sheets validation.
 * RFC 4180 (October 2005): https://www.rfc-editor.org/rfc/rfc4180.html
 * Python csv documentation: https://docs.python.org/3/library/csv.html
 */
'use strict';
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const {parseDelimited, exportCsv, withoutExactDuplicates, exportEvidenceJson} =
  require('../rescue-core.js');

let seed = 20261028;
function random() {
  seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
  return seed / 4294967296;
}
const tokens = ['a', '0', ',', '\t', '"', '\r', '\n', '\r\n',
  'é', '😀', ' ', '=', '+', '-', '@', '\u200B', 'ß'];
function cell() {
  return Array.from({length: Math.floor(random() * 12)},
    () => tokens[Math.floor(random() * tokens.length)]).join('');
}
const quote = value => '"' + value.replace(/"/g, '""') + '"';
const cases = [];
let sourceChecks = 0;
for (let index = 0; index < 600; index++) {
  const sep = index % 3 === 0 ? '\t' : ',';
  const width = 1 + Math.floor(random() * 6);
  const height = 1 + Math.floor(random() * 9);
  const headers = Array.from({length: width}, (_, n) => 'Column ' + (n + 1));
  const rows = Array.from({length: height},
    () => Array.from({length: width}, cell));
  // A deliberate nonadjacent duplicate checks original logical source IDs.
  if (index % 4 === 0 && height > 1) rows[height - 1] = rows[0].slice();
  const expected = [headers, ...rows];
  const text = sep === ',' ?
    exportCsv({headers, rows}, false) :
    expected.map(row => row.map(quote).join('\t')).join('\r\n');
  const parsed = parseDelimited(text, sep);
  assert.deepEqual(parsed.headers, headers, 'source headers case ' + index);
  assert.deepEqual(parsed.rows, rows, 'source values case ' + index);
  const seen = new Set(), positions = [], retained = [];
  rows.forEach((row, i) => {
    const key = JSON.stringify(row);
    if (!seen.has(key)) {
      seen.add(key);
      positions.push(i + 2);
      retained.push(row);
    }
  });
  const filtered = withoutExactDuplicates(parsed);
  const evidence = JSON.parse(exportEvidenceJson(filtered, 'synthetic.' +
    (sep === ',' ? 'csv' : 'tsv')));
  assert.deepEqual(evidence.records.map(r => r.sourceRecord), positions);
  assert.deepEqual(evidence.records.map(r => r.values), retained);
  assert.equal(evidence.source.originalDataRecords, height);
  sourceChecks += 3;
  cases.push({text, sep, expected});
}
// Independent Python csv.reader parses JS exports, and Python csv.writer
// produces a second encoding that the JS parser must read without cell loss.
// Python uses newline='' to retain embedded CR, LF, and CRLF in quoted fields.
const python = String.raw`
import csv
import io
import json
import sys

items = json.load(sys.stdin)
results = []
for item in items:
    delimiter = item["sep"]
    decoded = list(csv.reader(io.StringIO(item["text"], newline=""),
                              delimiter=delimiter, strict=True))
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL,
                        lineterminator="\r\n")
    writer.writerows(item["expected"])
    results.append({"decoded": decoded, "written": output.getvalue()})
json.dump(results, sys.stdout, ensure_ascii=False)
`;
const processResult = spawnSync('python3', ['-c', python], {
  input: JSON.stringify(cases), encoding: 'utf8',
  maxBuffer: 32 * 1024 * 1024, timeout: 60000
});
if (processResult.error || processResult.status !== 0)
  throw new Error('Independent Python CSV oracle failed: ' +
    (processResult.error || processResult.stderr));
const independent = JSON.parse(processResult.stdout);
assert.equal(independent.length, cases.length);
for (let i = 0; i < cases.length; i++) {
  assert.deepEqual(independent[i].decoded, cases[i].expected,
    'Python reads JS output case ' + i);
  const decoded = parseDelimited(independent[i].written, cases[i].sep);
  assert.deepEqual([decoded.headers, ...decoded.rows], cases[i].expected,
    'JS reads Python output case ' + i);
}
console.log('PASS: ' + cases.length +
  ' synthetic CSV/TSV cases; ' + (cases.length * 2) +
  ' independent Python read/JS read comparisons; ' +
  sourceChecks + ' source-position and exact-evidence checks.');
