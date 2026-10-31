'use strict';
// Synthetic-only regression for bounded, browser-local CSV export.
const assert = require('node:assert/strict');
const {exportCsv, exportCsvDownload, parseDelimited} = require('../rescue-core.js');
const LIMIT = 15_000_000;
let checks = 0;
function eq(a,b,label) { assert.deepStrictEqual(a,b,label); checks++; }
function blocked(fn,label) {
  assert.throws(fn,/CSV export exceeds the 15 MB output limit/,label);
  checks++;
}
const one = value => ({headers:['ID'],rows:[[value]]});
const bytes = value => Buffer.byteLength(value,'utf8');
const machineAtLimit = 'x'.repeat(LIMIT - 8); // "ID" CRLF "value"
eq(bytes(exportCsv(one(machineAtLimit),false)),LIMIT,'machine CSV exact 15 MB boundary');
blocked(() => exportCsv(one(machineAtLimit+'x'),false),'machine CSV one byte over');
blocked(() => exportCsvDownload(one(machineAtLimit+'x'),false),'machine download one byte over');
const sheetAtLimit = 'x'.repeat(LIMIT - 11); // reserve three UTF-8 BOM bytes
eq(bytes(exportCsvDownload(one(sheetAtLimit),true)),LIMIT,'spreadsheet CSV with BOM exact boundary');
blocked(() => exportCsvDownload(one(sheetAtLimit+'x'),true),'spreadsheet download over limit');
blocked(() => exportCsv(one(machineAtLimit),true),'spreadsheet mode reserves BOM');
blocked(() => exportCsv(one('é'.repeat(7_500_000)),false),'UTF-8 bytes not UTF-16 code units');
blocked(() => exportCsv(one('😀'.repeat(3_750_000)),false),'astral UTF-8 byte budget');
blocked(() => exportCsv(one('"'.repeat(8_000_000)),false),'quote doubling counted');
blocked(() => exportCsv({headers:Array(100).fill('H'),rows:Array(50000).fill(Array(100).fill('v'))},false),'many small cells exceed aggregate budget');
eq(parseDelimited(exportCsv({headers:['ID'],rows:Array(50000).fill(['v'])},false)).rows.length,50000,'50,000 narrow rows still supported');
eq(exportCsvDownload({headers:['A'],rows:[['=1+1']]},true),'\uFEFF"A"\r\n"\t=1+1"','formula precaution and BOM unchanged');
eq(exportCsv({headers:['A'],rows:[['=1+1']]},false),'"A"\r\n"=1+1"','machine CSV exact value unchanged');
eq(exportCsv({headers:['A'],rows:[['one\r\ntwo']]},false),'"A"\r\n"one\r\ntwo"','quoted CRLF retained');
const values=['','simple','a,b','"quoted"','é','😀','line\nfeed','@risk','=formula','  spaced  '];
let seed=0x514f5a1;
function next(){seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed;}
for(let i=0;i<500;i++){
  const v=values[next()%values.length];
  const csv=exportCsv({headers:['ID','Value'],rows:[[String(i),v]]},false);
  eq(parseDelimited(csv,',').rows,[[String(i),v]],'exact round trip '+i);
  assert.ok(bytes(csv)<=LIMIT);checks++;
}
console.log('FT-01 UTF-8 export budget: '+checks+'/'+checks+' PASS');
