/* Run with: node projects/data-rescue-studio/tests/rescue-core.test.js */
const assert = require('node:assert/strict');
const {parseDelimited, summarize, withoutExactDuplicates, exportCsv, formulaRisk} = require('../rescue-core.js');
const input = '\ufeffName,Note,Amount\r\n"Ada, L.","first\nsecond",12\r\nBob,"He said ""yes""",=1+2\r\nBob,"He said ""yes""",=1+2\r\n';
const parsed = parseDelimited(input);
assert.equal(parsed.rows.length, 3);
assert.equal(parsed.rows[0][0], 'Ada, L.');
assert.equal(parsed.rows[0][1], 'first\nsecond');
assert.equal(parsed.rows[1][1], 'He said "yes"');
assert.equal(summarize(parsed).duplicateRows.length, 1);
assert.equal(withoutExactDuplicates(parsed).rows.length, 2);
assert.deepEqual(parseDelimited('a\tb\none\ttwo').rows, [['one','two']]);
assert.equal(parseDelimited('x,x,\n1,2,3').normalizedHeaders[1], 'x (2)');
assert.equal(parseDelimited('a,b\n,0').rows[0][0], '');
assert.equal(formulaRisk(' \t=SUM(A1)'), true);
assert.equal(formulaRisk('@danger'), true);
assert.equal(formulaRisk('hello'), false);
assert.ok(exportCsv(parsed, true).includes('"\t=1+2"'));
assert.ok(exportCsv(parsed, false).includes('"=1+2"'));
assert.ok(exportCsv(parsed, true).includes('"first\nsecond"'));
assert.throws(() => parseDelimited('a,b\n"unclosed,x'), /Unclosed/);
assert.throws(() => parseDelimited('a,b\n1,2,3'), /No data was discarded/);
assert.throws(() => parseDelimited('a\nfoo"bar'), /Unexpected quote/);
console.log('PASS: 18 Data Rescue core assertions.');
// Reject formula-like cells with a TAB after whitespace; retain exact machine data.
for (const value of ['  \t=1+1', '\u00A0\t+SUM(A1)', ' \t＠SUM(A1)', ' \t＝1+1']) {
  const sample = parseDelimited('ID,Note\n1,"' + value + '"');
  assert.throws(() => exportCsv(sample, true), /source record 2, column 2/);
  assert.equal(parseDelimited(exportCsv(sample, false)).rows[0][1], value);
}
assert.throws(() => exportCsv(parseDelimited('ID,"  \t=1+1"\n1,ok'), true),
  /source record 1, column 2/);
assert.doesNotThrow(() => exportCsv(parseDelimited('ID,Note\n1,"  \tplain text"'), true));
console.log('PASS: 10 additional leading-TAB formula-boundary assertions.');

/*
 * Unicode U+2028 LINE SEPARATOR and U+2029 PARAGRAPH SEPARATOR are
 * explicit line boundaries in Unicode (Unicode Standard chapter 5).
 * Spreadsheet re-import behavior is not established; fail closed for the
 * spreadsheet-oriented CSV, while preserving exact machine CSV/JSON.
 * https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-5/
 * https://owasp.github.io/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Injection/21-CSV_Injection
 */
{
  const {exportEvidenceJson} = require('../rescue-core.js');
  for (const separator of ['\u2028', '\u2029']) {
    for (const payload of ['safe' + separator + '=1+1', 'safe' + separator + 'plain']) {
      const parsed = parseDelimited('ID,Note\n1,"' + payload + '"');
      assert.throws(() => exportCsv(parsed, true), /source record 2, column 2/);
      assert.equal(parseDelimited(exportCsv(parsed, false)).rows[0][1], payload);
      assert.equal(JSON.parse(exportEvidenceJson(parsed, 'synthetic.csv')).records[0].values[1], payload);
    }
    const header = parseDelimited('ID,"Name' + separator + 'Note"\n1,ok');
    assert.throws(() => exportCsv(header, true), /source record 1, column 2/);
    assert.equal(parseDelimited(exportCsv(header, false)).headers[1], 'Name' + separator + 'Note');
    const filtered = withoutExactDuplicates(parseDelimited(
      'ID,Note\n1,repeat\n1,repeat\n3,"safe' + separator + '=1+1"'));
    assert.throws(() => exportCsv(filtered, true), /source record 4, column 2/);
    assert.deepEqual(JSON.parse(exportEvidenceJson(filtered, 'synthetic.csv'))
      .records.map(r => r.sourceRecord), [2, 4]);
  }
  assert.doesNotThrow(() => exportCsv(parseDelimited('ID,Note\n1,"safe line"'), true));
  console.log('PASS: Unicode line/paragraph separator spreadsheet boundary and exact export checks.');
}




/*
 * Deterministic synthetic property checks (seed and case count fixed).
 * Machine CSV and explicit TSV must preserve decoded cell values, including
 * literal CR/LF, quotes, Unicode and formula-looking text. Expected duplicate
 * positions are computed from the original generated matrix, not from the
 * parser or the evidence exporter being tested.
 *
 * RFC 4180 (October 2005): https://www.rfc-editor.org/rfc/rfc4180.html
 * W3C CSV on the Web Primer (Working Group Note):
 * https://www.w3.org/TR/tabular-data-primer/
 * These tests do not establish spreadsheet reopen/resave safety.
 */
{
  const {exportEvidenceJson} = require('../rescue-core.js');
  let seed = 20261028;
  const random = () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  const characters = ['a','0',',','\t','"','\n','\r',' ','😀','é','\u200B','=','+','@','-'];
  const randomCell = () => Array.from({length: Math.floor(random() * 12)},
    () => characters[Math.floor(random() * characters.length)]).join('');
  const quoted = value => '"' + value.replace(/"/g, '""') + '"';
  for (let caseNumber = 0; caseNumber < 3000; caseNumber++) {
    const width = 1 + Math.floor(random() * 6);
    const height = 1 + Math.floor(random() * 10);
    const headers = Array.from({length: width}, (_, i) => 'Column ' + (i + 1));
    const rows = Array.from({length: height},
      () => Array.from({length: width}, randomCell));
    // Force nonadjacent duplicates, rather than relying on random collisions.
    if (caseNumber % 5 === 0 && height > 1) rows[height - 1] = rows[0].slice();
    const source = {headers, normalizedHeaders: headers, rows, warnings: [], delimiter: ','};
    const parsed = parseDelimited(exportCsv(source, false));
    assert.deepEqual(parsed.headers, headers, 'case ' + caseNumber + ': headers');
    assert.deepEqual(parsed.rows, rows, 'case ' + caseNumber + ': exact machine CSV cells');

    const expected = [], expectedPositions = [], seen = new Set();
    rows.forEach((row, index) => {
      const signature = JSON.stringify(row);
      if (!seen.has(signature)) {
        seen.add(signature);
        expected.push(row);
        expectedPositions.push(index + 2);
      }
    });
    const deduplicated = withoutExactDuplicates(parsed);
    assert.deepEqual(deduplicated.rows, expected, 'case ' + caseNumber + ': dedup');
    const evidence = JSON.parse(exportEvidenceJson(deduplicated, 'synthetic.csv'));
    assert.deepEqual(evidence.records.map(record => record.sourceRecord),
      expectedPositions, 'case ' + caseNumber + ': original source positions');
    assert.equal(evidence.source.originalDataRecords, height,
      'case ' + caseNumber + ': original record count');
    assert.deepEqual(evidence.records.map(record => record.values), expected,
      'case ' + caseNumber + ': exact JSON values');
    if (caseNumber % 3 === 0) {
      const tsv = [headers, ...rows].map(row => row.map(quoted).join('\t')).join('\r\n');
      assert.deepEqual(parseDelimited(tsv, '\t').rows, rows,
        'case ' + caseNumber + ': explicit TSV cells');
    }
  }
  console.log('PASS: 3,000 deterministic synthetic CSV/TSV and source-provenance scenarios.');
}

// Source-record review filters never mutate input or export selections.
// Whitespace-only cells count as missing, exact duplicate records cite the first source.
{
  const {inspectSourceRecords, exportEvidenceJson} = require('../rescue-core.js');
  const source = parseDelimited('ID,Note\n01,ok\n02," "\n03,ok\n03,ok\n04,"line one\nline two"\n');
  const before = JSON.stringify(source);
  const all = inspectSourceRecords(source, 'all');
  assert.deepEqual(all.entries.map(r => r.sourceRecord), [2,3,4,5,6]);
  assert.equal(all.total, 5);
  const missing = inspectSourceRecords(source, 'missing');
  assert.deepEqual(missing.entries.map(r => r.sourceRecord), [3]);
  const duplicate = inspectSourceRecords(source, 'duplicates');
  assert.deepEqual(duplicate.entries.map(r => [r.sourceRecord,r.duplicateOf]), [[5,4]]);
  assert.deepEqual(duplicate.entries[0].values, ['03','ok']);
  assert.deepEqual(inspectSourceRecords(source, 'all', 2).entries.map(r => r.sourceRecord), [2,3]);
  assert.equal(inspectSourceRecords(source, 'all', 2).total, 5);
  assert.equal(inspectSourceRecords(source, 'missing', 2).shown, 1);
  assert.deepEqual(inspectSourceRecords(source, 'duplicates', 1).entries[0].values, ['03','ok']);
  assert.throws(() => inspectSourceRecords(source, 'unexpected'), /review filter/);
  assert.throws(() => inspectSourceRecords(source, 'all', 0), /review filter/);
  assert.equal(JSON.stringify(source), before);
  assert.deepEqual(JSON.parse(exportEvidenceJson(source, 'synthetic.csv')).records.map(r => r.sourceRecord), [2,3,4,5,6]);
  const dedup = withoutExactDuplicates(source);
  assert.deepEqual(inspectSourceRecords(dedup, 'all').entries.map(r => r.sourceRecord), [2,3,4,6]);
  assert.deepEqual(inspectSourceRecords(dedup, 'duplicates').entries, []);
  console.log('PASS: 14 source-record issue-filter and provenance checks.');
}
