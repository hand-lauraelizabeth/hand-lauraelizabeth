'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const core = require('../rescue-core.js');
let checks = 0;
const eq = (actual, expected, label) => { assert.deepEqual(actual, expected, label); checks++; };
const throws = (fn, regex) => { assert.throws(fn, regex); checks++; };
const raw = 'ID,ID,Note,Empty\r\n"0007","0007","=1+2",\r\n"0007","0007","=1+2",\r\n"0008","0008","café\nline two",""';
const parsed = core.parseDelimited(raw);
const text = core.exportEvidenceJson(parsed, 'synthetic.CSV');
const doc = JSON.parse(text);
eq(doc.format, 'data-rescue-evidence', 'schema name');
eq(doc.schemaVersion, 1, 'version');
eq(doc.source.fileName, 'synthetic.CSV', 'filename retained');
eq(doc.source.delimiter, ',', 'delimiter retained');
eq(doc.source.headerRecord, 1, 'header logical record');
eq(doc.source.recordUnit, 'logical CSV/TSV record', 'logical record semantics');
eq(doc.headers, ['ID','ID','Note','Empty'], 'raw duplicate header names preserved');
eq(doc.normalizedHeaders, ['ID','ID (2)','Note','Empty'], 'display headers separate');
eq(doc.recordCount, 3, 'all source rows counted');
eq(doc.records.map(x=>x.sourceRecord), [2,3,4], 'source record indices');
eq(doc.records.map(x=>x.values), parsed.rows, 'every decoded field exact');
eq(doc.records[0].values[0], '0007', 'zero-padded identifier preserved');
eq(doc.records[0].values[2], '=1+2', 'formula-like text preserved without tab');
eq(doc.records[0].values[3], '', 'empty string retained, not null');
eq(doc.records[2].values[2], 'café\nline two', 'multiline and Unicode retained');
eq(doc.records[1].values, doc.records[0].values, 'duplicate row retained');
eq(doc.warnings.length > 0, true, 'duplicate header warning retained');
eq(core.exportCsv(parsed,true).includes('"\t=1+2"'), true, 'CSV precaution still separate');
eq(doc.records[0].values[2].startsWith('\t'), false, 'JSON never changes formula cell');
const tab = core.parseDelimited('key\tvalue\r\n0002\t"@SUM(A1)"', '\t');
eq(JSON.parse(core.exportEvidenceJson(tab)).records[0].values, ['0002','@SUM(A1)'], 'TSV decoded cells exact');
eq(JSON.parse(core.exportEvidenceJson(tab)).source.delimiter, '\t', 'TSV delimiter retained');
for(const broken of [
 null, {}, {headers:[], normalizedHeaders:[], rows:[], warnings:[], delimiter:','},
 {...parsed, rows:[['short']]}, {...parsed, headers:['ID']},
 {...parsed, rows:[[1,2,3,4]]}, {...parsed, warnings:[null]},
 {...parsed, delimiter:';'}, {...parsed, normalizedHeaders:[]},
 {...parsed, rows:Array.from({length:50001},()=>['a','b','c','d'])}
]) throws(()=>core.exportEvidenceJson(broken), /parsed CSV|incomplete|inconsistent/);
throws(()=>core.exportEvidenceJson(parsed, {secret:true}), /parsed CSV/);
const source = fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
eq(source.includes('id="saveJson" disabled'), true, 'JSON button initially disabled');
eq(source.includes("'saveJson').disabled=true"), true, 'JSON button cleared on reset');
eq(source.includes("'saveJson').disabled=false"), true, 'JSON button enabled on load');
eq(source.includes("lib.exportEvidenceJson(loaded"), true, 'JSON uses original loaded rows');
eq(source.includes("type:'application/json;charset=utf-8'"), true, 'JSON MIME type');
eq(source.includes("data-rescue-evidence.json"), true, 'JSON filename');
eq(source.includes("Both downloads contain your data"), true, 'privacy notice');
eq(source.includes("not a byte-for-byte copy"), true, 'provenance limitation');
console.log('PASS: '+checks+' exact JSON provenance, privacy and UI contract assertions.');
