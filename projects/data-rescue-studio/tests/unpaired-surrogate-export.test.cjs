'use strict';
// Synthetic-only: prevent UTF-8 encoding from silently replacing lone UTF-16 surrogates.
const assert = require('node:assert/strict');
const {parseDelimited, exportCsv, exportCsvDownload, exportEvidenceJson} =
  require('../rescue-core.js');
let checks = 0;
function verify(fn) { fn(); checks++; }
function table(value, header = 'ID') {
  return {headers: [header], normalizedHeaders: [header], rows: [[value]],
    warnings: [], delimiter: ','};
}
const malformed = [
  '\uD800', '\uDBFF', '\uDC00', '\uDFFF', 'x\uD800',
  '\uD800x', '\uD800\uD800\uDC00', '\uDC00\uD800',
  '\uD800\uDC00\uDFFF', '\uD800\uD800', '\uDFFF\uD800\uDC00',
  'valid 😀 then \uDC00'
];
for (const value of malformed) {
  verify(() => assert.equal(value.isWellFormed(), false));
  const parsed = table(value);
  const before = JSON.stringify(parsed);
  for (const spreadsheetView of [false, true]) {
    verify(() => assert.throws(() => exportCsv(parsed, spreadsheetView),
      /unmatched UTF-16 surrogate at table record 2, column 1/));
    verify(() => assert.throws(() => exportCsvDownload(parsed, spreadsheetView),
      /unmatched UTF-16 surrogate at table record 2, column 1/));
  }
  // Exact evidence JSON remains available, without converting source code units.
  verify(() => assert.equal(JSON.parse(exportEvidenceJson(parsed)).records[0].values[0], value));
  verify(() => assert.equal(JSON.stringify(parsed), before));
}
for (const header of ['\uD800', 'a\uDFFF']) {
  const parsed = table('safe', header);
  for (const spreadsheetView of [false, true]) {
    verify(() => assert.throws(() => exportCsv(parsed, spreadsheetView),
      /unmatched UTF-16 surrogate at table record 1, column 1/));
    verify(() => assert.throws(() => exportCsvDownload(parsed, spreadsheetView),
      /unmatched UTF-16 surrogate at table record 1, column 1/));
  }
  verify(() => assert.equal(JSON.parse(exportEvidenceJson(parsed)).headers[0], header));
}
const valid = ['plain', '😀', 'x🧪y', 'a"b', 'a\nb', '\uFFFD', '🧬🧪', 'é', '😀😀', 'a\r\nb'];
for (const value of valid) {
  verify(() => assert.equal(value.isWellFormed(), true));
  const parsed = table(value);
  for (const spreadsheetView of [false, true]) {
    const csv = exportCsvDownload(parsed, spreadsheetView);
    verify(() => assert.equal(parseDelimited(csv, ',').rows[0][0], value));
    verify(() => assert.equal(csv.charCodeAt(0) === 0xFEFF, spreadsheetView));
  }
}
// Node's UTF-8 encoder replaces a lone surrogate; the rejection prevents this loss.
verify(() => assert.equal(Buffer.from('\uD800', 'utf8').toString('hex'), 'efbfbd'));
verify(() => assert.equal(Buffer.from('😀', 'utf8').toString('hex'), 'f09f9880'));
console.log('FT-01 unmatched UTF-16 CSV export: ' + checks + '/' + checks + ' PASS');
