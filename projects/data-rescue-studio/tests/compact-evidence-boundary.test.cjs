'use strict';
// Synthetic worst-shape acceptance for browser-local JSON evidence.
// Verifies source identity, lossless cells, and bounded serialization overhead.
const assert = require('node:assert/strict');
const {parseDelimited, exportEvidenceJson, withoutExactDuplicates, MAX_BYTES} = require('../rescue-core.js');
const {byteLength} = Buffer;
let checks = 0;
function eq(actual, expected, message) {assert.deepEqual(actual, expected, message); checks++;}
function ok(value, message) {assert.ok(value, message); checks++;}

const headers = ['ID', 'ID', 'Note', ...Array.from({length:97}, (_,i)=>'C'+i)];
const blank = ','.repeat(99);
const lines = Array(49_000).fill(blank);
lines[0] = '0007,=1+2,"café\nline",' + ','.repeat(97);
lines[48_999] = '0099,-2,tail,' + ','.repeat(97);
const source = headers.join(',') + '\r\n' + lines.join('\r\n');
const sourceBytes = byteLength(source, 'utf8');
ok(sourceBytes <= MAX_BYTES && sourceBytes > 4_900_000, 'near-limit synthetic CSV remains under byte cap');
const parsed = parseDelimited(source);
eq(parsed.rows.length, 49_000, '49k logical source rows retained');
eq(parsed.headers.length, 100, '100 columns retained');
eq(parsed.headers.slice(0,2), ['ID','ID'], 'duplicate raw header preserved');
eq(parsed.normalizedHeaders.slice(0,2), ['ID','ID (2)'], 'display header disambiguated');
eq(parsed.rows[0].slice(0,3), ['0007','=1+2','café\nline'], 'leading zeros, formula-like text, Unicode and multiline preserved');
eq(parsed.rows.at(-1).slice(0,3), ['0099','-2','tail'], 'last source row retained');
const digest = 'a'.repeat(64);
const compact = exportEvidenceJson(parsed, 'synthetic.csv', {byteCount:sourceBytes, sha256:digest});
const compactBytes = byteLength(compact, 'utf8');
ok(compactBytes < 20_000_000, '49k x 100 compact evidence stays below 20 MB');
const evidence = JSON.parse(compact);
eq(evidence.format, 'data-rescue-evidence', 'schema identifier retained');
eq(evidence.schemaVersion, 1, 'schema version unchanged');
eq(evidence.source.byteCount, sourceBytes, 'original source byte count retained');
eq(evidence.source.sha256, digest, 'validated original-byte digest retained');
eq(evidence.headers, parsed.headers, 'original raw header values retained');
eq(evidence.normalizedHeaders, parsed.normalizedHeaders, 'normalized display headers retained');
eq(evidence.recordCount, 49_000, 'source record count retained');
eq(evidence.records.length, 49_000, 'all records included');
eq(evidence.records[0], {sourceRecord:2,values:parsed.rows[0]}, 'first record exact values and position');
eq(evidence.records.at(-1), {sourceRecord:49_001,values:parsed.rows.at(-1)}, 'last record exact values and position');
ok(!compact.includes('\n  "format"'), 'JSON has no unnecessary formatting indentation');
const prettyBytes = byteLength(JSON.stringify(evidence,null,2), 'utf8');
ok(compactBytes < prettyBytes * 0.35, 'compact output uses under 35% of prior pretty output');
const duplicate = parseDelimited('ID,Value\n0001,=2+2\n0001,=2+2\n');
eq(withoutExactDuplicates(duplicate).rows.length,1,'deduplication is optional');
eq(JSON.parse(exportEvidenceJson(duplicate,'example.csv')).records.map(r=>r.sourceRecord),[2,3],'JSON evidence retains duplicate source positions');
ok(!Object.hasOwn(JSON.parse(exportEvidenceJson(duplicate,'example.csv')).source,'sha256'),'missing fingerprint is not invented');
assert.throws(()=>exportEvidenceJson(duplicate,'example.csv',{sha256:'not-a-digest',byteCount:10}),/Invalid original-file/); checks++;
console.log('PASS: '+checks+' compact JSON evidence assertions; '+sourceBytes+' input bytes; '+compactBytes+' compact output bytes vs '+prettyBytes+' prior pretty bytes.');
