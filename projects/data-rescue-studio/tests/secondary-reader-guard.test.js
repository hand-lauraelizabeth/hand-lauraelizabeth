'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'..','reconcile-ui.js'),'utf8');
assert.ok(source.includes('DataRescueFileReader.read(file, lib.parseDelimited)'),'second-file import must use strict reader');
assert.ok(source.includes('thisGeneration !== generation'),'stale async reads must not overwrite current data');
assert.ok(source.includes('compareExport').toString(),'comparison audit export must remain explicit');
console.log('PASS: 3 secondary-file reader invariants.');
