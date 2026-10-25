'use strict';
// Synthetic CSV/TSV values only. Spreadsheet-friendly downloads are not evidence exports.
const assert=require('node:assert/strict');
const {parseDelimited,exportCsv,exportCsvDownload,exportEvidenceJson}=require('../rescue-core.js');
let checks=0;
function eq(a,b,m){assert.deepEqual(a,b,m);checks++;}
function ok(a,m){assert.ok(a,m);checks++;}
const source='ID,Note,Formula,Multiline\r\n0007,café,=1+2,"line one\nline two"\r\n0007,café,=1+2,"line one\nline two"\r\n=x,漢字,+SUM(1),safe\r\n';
const parsed=parseDelimited(source);
const before=JSON.stringify(parsed);
const spreadsheet=exportCsvDownload(parsed,true);
eq(Buffer.from(spreadsheet,'utf8').subarray(0,3),Buffer.from([0xef,0xbb,0xbf]),'Excel-friendly export starts with UTF-8 BOM bytes');
eq(spreadsheet.charCodeAt(0),0xfeff,'exactly one BOM code point at start');
eq(spreadsheet.slice(1),exportCsv(parsed,true),'BOM changes only encoding preamble, not protected CSV cells');
const reopened=parseDelimited(spreadsheet);
eq(reopened.headers,parsed.headers,'BOM does not become part of first header');
eq(reopened.rows.length,3,'duplicates survive spreadsheet CSV round-trip');
eq(reopened.rows[0][0],'0007','zero-padded identifier preserved as CSV text');
eq(reopened.rows[0][1],'café','accented UTF-8 preserved');
eq(reopened.rows[0][2],'\t=1+2','formula-like cell prefixed in spreadsheet-oriented mode');
eq(reopened.rows[2][0],'\t=x','formula-like identifier prefixed');
eq(reopened.rows[2][1],'漢字','CJK characters preserved');
eq(reopened.rows[2][2],'\t+SUM(1)','formula-like plus cell prefixed');
eq(reopened.rows[0][3],'line one\nline two','multiline quoted cell preserved');
const machine=exportCsvDownload(parsed,false);
ok(!machine.startsWith('\uFEFF'),'machine CSV has no BOM');
eq(machine,exportCsv(parsed,false),'machine CSV matches pre-existing exact export');
eq(parseDelimited(machine).rows,parsed.rows,'machine CSV round-trip preserves exact decoded cells');
eq(JSON.parse(exportEvidenceJson(parsed,'synthetic.csv')).records[2].values,parsed.rows[2],'JSON evidence retains original unmodified values');
eq(JSON.stringify(parsed),before,'neither download mutates parsed source');
eq(exportCsvDownload(parsed),spreadsheet,'default remains spreadsheet-oriented');
const empty=parseDelimited('ID,Value\n');
eq(parseDelimited(exportCsvDownload(empty,true)).rows,[],'header-only CSV round-trip');
ok(!spreadsheet.slice(1).startsWith('\uFEFF'),'no duplicate BOM');
console.log('PASS: '+checks+' independent UTF-8 BOM, exact machine CSV, formula, Unicode and evidence checks.');
