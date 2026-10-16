import assert from 'node:assert/strict';
import {csvCell} from './engine.mjs';
const prefixes = ['＝', '＋', '－', '＠'];
for (const prefix of prefixes) {
  const cell = csvCell(prefix + 'SUM(1,2)');
  assert.ok(cell.startsWith('"\u0027'));
}
console.log('PASS: four fullwidth prefixes');
