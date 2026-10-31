'use strict';
// Synthetic-only regression for bounded Unicode reconciliation previews.
// The reference deliberately materializes small strings; the implementation
// is evaluated with Array.from disabled to catch full-array regressions.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '..', 'reconcile-ui.js'), 'utf8');
const match = source.match(/(function auditPreview\(value\) \{[\s\S]*?\n  \})\n  \/\/ Preview-only descriptions/);
assert.ok(match, 'extract exact committed preview function');
const sandbox = vm.createContext({});
vm.runInContext('Array.from = () => { throw Error("full-array materialization forbidden"); }', sandbox);
const preview = vm.runInContext('(' + match[1] + ')', sandbox);
function reference(value) {
  const points = Array.from(String(value));
  const omitted = Math.max(0, points.length - 116);
  const shown = omitted ? [...points.slice(0, 96), ...points.slice(-20)] : points;
  const visible = shown.map(char => {
    const code = char.codePointAt(0);
    if (char === '\n') return '\\n';
    if (char === '\r') return '\\r';
    if (char === '\t') return '\\t';
    if (code < 32 || (code >= 127 && code <= 159) || /\p{Default_Ignorable_Code_Point}/u.test(char))
      return '\\u{' + code.toString(16).toUpperCase().padStart(4, '0') + '}';
    return char;
  });
  if (omitted) visible.splice(96, 0, ' … [' + omitted + ' code points omitted] … ');
  return visible.join('');
}
let checks = 0;
function equal(actual, expected, label) { assert.equal(actual, expected, label); checks++; }
const chars = ['A','é','😀','\n','\r','\t','\u0000','\u007f','\u200d','\u202e','\u2066','\u0301','𝄞','Z'];
for (const length of [0,1,20,95,96,97,115,116,117,118,136,300]) {
  const value = Array.from({length}, (_, i) => chars[i % chars.length]).join('');
  equal(preview(value), reference(value), 'code-point boundary '+length);
}
for (let i = 0; i < 4000; i++) {
  const length = (i * 37) % 280;
  let value = '';
  for (let j = 0; j < length; j++) value += chars[(i + j * 7) % chars.length];
  equal(preview(value), reference(value), 'deterministic Unicode case '+i);
}
const long = '😀'.repeat(1_200_000) + 'END';
const result = preview(long);
assert.ok(result.length < 300, 'long preview is bounded'); checks++;
assert.ok(result.startsWith('😀'.repeat(96)), 'prefix retains code points'); checks++;
assert.ok(result.endsWith('😀'.repeat(17) + 'END'), 'suffix retains code points'); checks++;
assert.ok(result.includes('[1199887 code points omitted]'), 'exact omitted count'); checks++;
equal(long.codePointAt(0), 0x1f600, 'input unchanged');
console.log('FT-03 bounded reconciliation preview: '+checks+'/'+checks+' PASS');
