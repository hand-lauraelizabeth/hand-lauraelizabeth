'use strict';
// Synthetic records only. Newlines inside quoted fields are exact decoded cell data.
const assert=require('node:assert/strict');
const {parseDelimited,exportCsvDownload,exportEvidenceJson,withoutExactDuplicates,summarize}=require('../rescue-core.js');
let count=0;
function eq(actual,expected,label){assert.deepEqual(actual,expected,label);count++;}
function ok(value,label){assert.ok(value,label);count++;}
const source='\uFEFFID,Note,Symbol\r\n' +
  '0001,"first\r\nsecond",café\r\n' +
  '0002,"first\rsecond",漢字\r\n' +
  '0003,"first\nsecond",safe\r\n' +
  '0004,"embedded ""quote""\r\nand \r then \n",safe\r\n' +
  '0004,"embedded ""quote""\r\nand \r then \n",safe\r\n';
const parsed=parseDelimited(source);
eq(parsed.headers,['ID','Note','Symbol'],'raw headers');
eq(parsed.rows.length,5,'record count');
eq(parsed.rows[0][1],'first\r\nsecond','CRLF retained inside quote');
eq(parsed.rows[1][1],'first\rsecond','lone CR retained inside quote');
eq(parsed.rows[2][1],'first\nsecond','LF retained inside quote');
eq(parsed.rows[3][1],'embedded "quote"\r\nand \r then \n','mixed breaks and escaped quotes retained');
eq(parsed.rows[4],parsed.rows[3],'duplicate record exact');
eq(summarize(parsed).duplicateRows,[{row:6,firstSeen:5}],'duplicate logical source positions');
const evidence=JSON.parse(exportEvidenceJson(parsed,'synthetic-mixed-newlines.csv'));
eq(evidence.recordCount,5,'evidence record count');
eq(evidence.records.map(x=>x.sourceRecord),[2,3,4,5,6],'logical source records not physical lines');
eq(evidence.records.map(x=>x.values),parsed.rows,'JSON retains exact decoded cell characters');
eq(evidence.source.fileName,'synthetic-mixed-newlines.csv','source filename');
eq(evidence.source.recordUnit,'logical CSV/TSV record','source record unit');
const machine=exportCsvDownload(parsed,false);
ok(!machine.startsWith('\uFEFF'),'machine CSV has no BOM');
eq(parseDelimited(machine).rows,parsed.rows,'machine CSV round-trip exact');
const spreadsheet=exportCsvDownload(parsed,true);
ok(spreadsheet.startsWith('\uFEFF'),'spreadsheet CSV has BOM');
eq(parseDelimited(spreadsheet).rows,parsed.rows,'spreadsheet CSV round-trip exact when no formula-risk cells');
eq(withoutExactDuplicates(parsed).rows.length,4,'deduplication still removes only identical decoded records');
const tsv=parseDelimited('ID\tNotes\r\n001\t"alpha\r\nbeta"\r\n002\t"alpha\rbeta"\r\n');
eq(tsv.delimiter,'\t','TSV detected');
eq(tsv.rows.map(x=>x[1]),['alpha\r\nbeta','alpha\rbeta'],'TSV quoted newline variants preserved');
eq(parseDelimited(exportCsvDownload(tsv,false)).rows,tsv.rows,'TSV to CSV machine export exact');
const embedded=parseDelimited('ID,Note\n01,"one\r\n\r\n two"\n');
eq(embedded.rows[0][1],'one\r\n\r\n two','consecutive CRLF sequences retained');
eq(parseDelimited(exportCsvDownload(embedded,false)).rows,embedded.rows,'consecutive CRLF round-trip');
console.log('PASS: '+count+' exact quoted CRLF/CR/LF, JSON provenance, CSV and TSV assertions.');
