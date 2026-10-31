'use strict';
// Synthetic-only regression: parser input limits are UTF-8 bytes, not UTF-16 units.
const assert = require('node:assert/strict');
const {parseDelimited, MAX_BYTES} = require('../rescue-core.js');
let checks = 0;
function accepts(input, label) {
  assert.ok(Buffer.byteLength(input, 'utf8') <= MAX_BYTES, label + ' fixture budget');
  const parsed = parseDelimited(input, ',');
  assert.equal(parsed.headers[0], 'ID', label + ' header');
  assert.equal(parsed.rows.length, 1, label + ' record count');
  checks += 3;
  return parsed.rows[0][0];
}
function rejects(input, label) {
  assert.ok(input.length <= MAX_BYTES || Buffer.byteLength(input, 'utf8') > MAX_BYTES,
    label + ' fixture sanity');
  assert.ok(Buffer.byteLength(input, 'utf8') > MAX_BYTES, label + ' byte count');
  assert.throws(() => parseDelimited(input, ','), /5 MB UTF-8 byte limit/, label);
  checks += 3;
}
assert.equal(MAX_BYTES, 5_000_000); checks++;
assert.equal(accepts('ID\nÉlodie', 'ordinary Unicode'), 'Élodie'); checks++;
const exact = 'ID\n' + 'é'.repeat(2_499_998) + 'x';
assert.equal(Buffer.byteLength(exact, 'utf8'), MAX_BYTES); checks++;
assert.equal(accepts(exact, 'exact 5 MB UTF-8').length, 2_499_999); checks++;
rejects('ID\n' + 'é'.repeat(2_500_000), 'two-byte characters exceed bytes but not code units');
rejects('ID\n' + '😀'.repeat(1_250_000), 'four-byte characters exceed bytes but not code units');
const withBom = '\uFEFFID\n' + 'é'.repeat(2_499_997);
assert.equal(Buffer.byteLength(withBom, 'utf8'), MAX_BYTES); checks++;
assert.equal(accepts(withBom, 'exact 5 MB with BOM').length, 2_499_997); checks++;
rejects(withBom + 'x', 'BOM counted in original byte budget');
rejects('ID\n' + 'a'.repeat(4_999_998), 'ASCII one byte over');
assert.throws(() => parseDelimited(42), /Input must be text/); checks++;
console.log('FT-01 UTF-8 input budget: ' + checks + '/' + checks + ' PASS');
