import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

// The browser entry point and every direct dependency must ship together.
const root = dirname(fileURLToPath(import.meta.url));
const required = ['index.html','app.mjs','styles.css','core.mjs',
  'evidence-coverage.mjs','reopen.mjs','replacement-gate.mjs','reset-gate.mjs'];
for (const name of required) {
  assert.ok(existsSync(resolve(root,name)), 'Missing browser release dependency: '+name);
}
const html = readFileSync(resolve(root,'index.html'),'utf8');
assert.match(html, /<script[^>]+src="app\.mjs"/);
const app = readFileSync(resolve(root,'app.mjs'),'utf8');
for (const name of ['core.mjs','evidence-coverage.mjs','reopen.mjs','replacement-gate.mjs','reset-gate.mjs']) {
  assert.ok(app.includes("'./"+name+"'"), 'Browser module import missing: '+name);
}
console.log('FT-07 browser release closure: 14 assertions passed');
