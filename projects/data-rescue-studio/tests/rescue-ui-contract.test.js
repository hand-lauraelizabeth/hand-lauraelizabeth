/* Browser upload and export contract checks for Data Rescue Studio. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const core = require('../rescue-core.js');
const checks = [
  ['local file selector', /type="file"[^>]*accept="[^"]*\.csv/.test(html)],
  ['input has visible label', /<label for="file">/.test(html)],
  ['status announced', /id="status"[^>]*role="status"/.test(html)],
  ['file size checked before reading', html.indexOf('file.size>lib.MAX_BYTES') < html.indexOf('await file.text()')],
  ['input filename extension checked', /\/\\\.\(csv\|tsv\)/.test(html) || html.includes('test(file.name)')],
  ['export via local Blob', html.includes('new Blob([csv]')],
  ['object URL revoked', html.includes('URL.revokeObjectURL')],
  ['no network upload code', !/\bfetch\(|XMLHttpRequest|sendBeacon|\.submit\(/.test(html)],
  ['duplicate removal is opt-in', /id="dedupe"[^>]*disabled/.test(html)],
  ['spreadsheet formula caveat displayed', html.includes('not universally safe')]
];
for (const [name, ok] of checks) assert.ok(ok, name);
assert.throws(() => core.parseDelimited('a,b\n1,2,3'), /No data was discarded/);
assert.equal(core.parseDelimited('a,b\n"quoted, value",x').rows[0][0], 'quoted, value');
assert.equal(core.formulaRisk('=HYPERLINK("x")'), true);
console.log('PASS: 13 Data Rescue UI contract and malformed-input checks.');
