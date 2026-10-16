'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
const reconcile = fs.readFileSync(path.join(__dirname,'reconcile-ui.js'),'utf8');
test('error messages are keyboard focusable', () => {
  assert.match(html, /id="status"[^>]*tabindex="-1"/);
  assert.match(html, /id="compareStatus"[^>]*tabindex="-1"/);
});
test('secondary imports require strict local reader', () => {
  assert.match(reconcile, /DataRescueFileReader\.read\(file, lib\.parseDelimited\)/);
  assert.doesNotMatch(reconcile, /await file\.text\(/);
});
