'use strict';
// Synthetic-only regression: CSV error messages must identify original logical
// source records after filtering, and both CSV modes must reject bad provenance.
const assert = require('node:assert/strict');
const {parseDelimited, exportCsv, exportCsvDownload, exportEvidenceJson} =
  require('../rescue-core.js');
let checks = 0;
function check(fn) { fn(); checks++; }
function table(values, metadata = {}) {
  return {headers:['ID'], normalizedHeaders:['ID'],
    rows:values.map(v=>[v]), warnings:[], delimiter:',', ...metadata};
}
const original = table(['safe','\uD800'], {sourceRecords:[2,7], originalRowCount:6});
const snapshot = JSON.stringify(original);
for (const mode of [false,true]) {
  for (const exportFn of [exportCsv, exportCsvDownload]) {
    check(()=>assert.throws(()=>exportFn(original,mode),
      /at table record 3, column 1 \(original source record 7\)/));
  }
}
check(()=>assert.equal(JSON.stringify(original),snapshot));
check(()=>assert.deepEqual(JSON.parse(exportEvidenceJson(original)).records
  .map(r=>r.sourceRecord),[2,7]));
check(()=>assert.equal(JSON.parse(exportEvidenceJson(original)).records[1].values[0],'\uD800'));
const invalid = [
  {originalRowCount:6}, // filtered with unknown original positions
  {sourceRecords:[2],originalRowCount:6}, // incomplete positions
  {sourceRecords:[2,2],originalRowCount:6}, // duplicate positions
  {sourceRecords:[7,2],originalRowCount:6}, // reversed positions
  {sourceRecords:[2,8],originalRowCount:6}, // impossible position
  {sourceRecords:[1,7],originalRowCount:6}, // header record used as data
  {sourceRecords:[2,'7'],originalRowCount:6}, // non-integer
  {sourceRecords:[2,7],originalRowCount:1}, // impossible source count
];
for (const metadata of invalid) {
  const parsed=table(['safe','safe'],metadata);
  // Exact machine CSV does not claim source IDs and must remain available.
  check(()=>assert.deepEqual(parseDelimited(exportCsv(parsed,false),',').rows,parsed.rows));
  check(()=>assert.deepEqual(parseDelimited(exportCsvDownload(parsed,false),',').rows,parsed.rows));
  // Spreadsheet CSV reports original positions when evaluating risky cells.
  check(()=>assert.throws(()=>exportCsv(parsed,true),
    /source-record|original source-record/i));
  check(()=>assert.throws(()=>exportCsvDownload(parsed,true),
    /source-record|original source-record/i));
  // If machine CSV must report a Unicode error, it cannot invent its source ID.
  const malformed=table(['safe','\\uD800'],metadata);
  check(()=>assert.throws(()=>exportCsv(malformed,false),
    /source-record|original source-record/i));
}
for (const mode of [false,true]) {
  const clean=table(['é','😀'],{sourceRecords:[2,7],originalRowCount:6});
  check(()=>assert.deepEqual(parseDelimited(exportCsvDownload(clean,mode),',').rows,clean.rows));
  const normal=table(['safe','safe']);
  check(()=>assert.deepEqual(parseDelimited(exportCsvDownload(normal,mode),',').rows,normal.rows));
  check(()=>assert.throws(()=>exportCsv(table(['safe','\uD800']),mode),
    /at table record 3, column 1 \(original source record 3\)/));
  check(()=>assert.throws(()=>exportCsv({...table(['safe']),headers:['\uD800']},mode),
    /at table record 1, column 1 \(original source record 1\)/));
}
check(()=>assert.equal(parseDelimited(exportCsv(table(['=1+2']),true),',').rows[0][0], '\t=1+2'));
console.log('FT-01 CSV original-record integrity: '+checks+'/'+checks+' PASS');
