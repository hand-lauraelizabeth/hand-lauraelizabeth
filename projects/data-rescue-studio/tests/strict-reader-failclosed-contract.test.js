const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ui=fs.readFileSync(path.join(__dirname,'..','reconcile-ui.js'),'utf8');
assert.match(ui,/Strict local file reader is unavailable/);
assert.match(ui,/DataRescueFileReader\.read\(file, lib\.parseDelimited\)/);
assert.doesNotMatch(ui,/await file\.text\(\)/);
console.log('PASS: 3 strict-reader fail-closed contracts.');
