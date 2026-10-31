'use strict';
// Synthetic-only CSV shape and evidence-integrity regression.
const assert = require('node:assert/strict');
const {parseDelimited, exportCsv, exportCsvDownload, spreadsheetExportRisk} = require('../rescue-core.js');
let checks = 0;
function equal(actual, expected, label) { assert.deepStrictEqual(actual, expected, label); checks++; }
function rejects(fn, label) {
  assert.throws(fn, /incomplete or inconsistent CSV table/, label);
  checks++;
}
const base = () => ({headers:['ID','Value'], rows:[['A','one']], sourceRecords:[2], originalRowCount:1});
const poison = {toString() { throw Error('must not coerce an untrusted cell'); }};
const malformed = [
  ['short record', {...base(), rows:[['A']]}],
  ['extra cell', {...base(), rows:[['A','one','untracked']]}],
  ['nonstring cell', {...base(), rows:[[7,'one']]}],
  ['missing cell', {...base(), rows:[['A',undefined]]}],
  ['null row', {...base(), rows:[null]}],
  ['object cell', {...base(), rows:[['A',poison]]}],
  ['nonarray rows', {...base(), rows:'A,one'}],
  ['null rows', {...base(), rows:null}],
  ['missing headers', {...base(), headers:null}],
  ['empty headers', {...base(), headers:[]}],
  ['nonstring header', {...base(), headers:['ID',false]}],
  ['too many headers', {...base(), headers:Array(101).fill('x')}],
  ['too many records', {...base(), rows:Array(50001).fill(['A','one'])}],
  ['missing table', null]
];
for (const [name, value] of malformed) {
  for (const spreadsheet of [false, true]) {
    rejects(() => exportCsv(value, spreadsheet), name+' CSV mode '+spreadsheet);
    rejects(() => exportCsvDownload(value, spreadsheet), name+' download mode '+spreadsheet);
  }
  rejects(() => spreadsheetExportRisk(value), name+' direct risk check');
}
equal(exportCsv(base(), false), '"ID","Value"\r\n"A","one"', 'ordinary exact machine CSV');
equal(exportCsv(base(), true), '"ID","Value"\r\n"A","one"', 'ordinary spreadsheet CSV');
equal(exportCsvDownload(base(), true), '\uFEFF"ID","Value"\r\n"A","one"', 'spreadsheet BOM preserved');
equal(exportCsvDownload(base(), false), '"ID","Value"\r\n"A","one"', 'machine CSV BOM-free');
equal(exportCsv({...base(),rows:[]},false), '"ID","Value"', 'header-only CSV');
equal(exportCsv({headers:['A'],rows:[['']],sourceRecords:[2],originalRowCount:1},false), '"A"\r\n""', 'blank cell retained');
equal(exportCsv({headers:['A'],rows:[['=1+1']],sourceRecords:[2],originalRowCount:1},false), '"A"\r\n"=1+1"', 'machine CSV retains exact risky value');
equal(exportCsv({headers:['A'],rows:[['=1+1']],sourceRecords:[2],originalRowCount:1},true), '"A"\r\n"\t=1+1"', 'spreadsheet CSV retains existing mitigation; no resave-safety claim');
equal(exportCsv({headers:Array(100).fill('H'),rows:[Array(100).fill('v')]},false).split('\r\n')[0].split(',').length,100,'100-column limit accepted');
equal(exportCsv({headers:['A'],rows:Array(50000).fill(['v'])},false).split('\r\n').length,50001,'50,000-row limit accepted');
let seed=0x61ca5e;
function next() {seed=(Math.imul(seed,1664525)+1013904223)>>>0; return seed;}
const corpus=['plain','a,b','two"quotes','line\nfeed','return\rline','CRLF\r\ninside',' café ','😀','','@risk','=formula'];
for(let i=0;i<1000;i++) {
  const table={headers:['ID','Value'],rows:[[String(i),corpus[next()%corpus.length]]]};
  const csv=exportCsv(table,false);
  const roundTrip=parseDelimited(csv,',');
  equal(roundTrip.headers,table.headers,'header roundtrip '+i);
  equal(roundTrip.rows,table.rows,'exact machine CSV roundtrip '+i);
}
console.log('FT-01 export table shape: '+checks+'/'+checks+' PASS');
