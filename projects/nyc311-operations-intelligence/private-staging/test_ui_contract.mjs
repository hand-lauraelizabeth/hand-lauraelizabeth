import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const html = readFileSync(new URL('./index.html', import.meta.url),'utf8');
const app = readFileSync(new URL('./app.mjs', import.meta.url),'utf8');
test('document has a main landmark, a single primary heading and named controls', () => {
  assert.match(html, /<html lang="en">/);
  assert.match(html, /<main id="main">/);
  assert.equal((html.match(/<h1\b/g)||[]).length,1);
  for(const id of ['file','month','borough','agency','query','sort']) assert.match(html,new RegExp(`<label for="${id}">`));
});
test('chart has textual list semantics and the table has a caption', () => {
  assert.match(html, /<ol id="bars"/);
  assert.match(html, /<caption id="table-caption">/);
  assert.match(app, /track\.setAttribute\('aria-hidden','true'\)/);
});
test('upload errors clear previously loaded data and announce errors', () => {
  assert.match(app, /catch \(error\) \{ clearData\(\); status\(`Rejected:/);
  assert.match(app, /if \(file\.size > 8_000_000\) \{ clearData\(\);/);
  assert.match(app, /setAttribute\('role', isError \? 'alert' : 'status'\)/);
});
test('new files reset all controls and data stays local', () => {
  assert.match(app, /resetFilters\(\);\n  status\(/);
  assert.doesNotMatch(app, /\bfetch\s*\(|XMLHttpRequest|sendBeacon/);
});
