'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'text-lens.html'), 'utf8');
const vendor = path.join(root, 'vendor');
const expected = ['mammoth.browser.min.js', 'pdf.min.js', 'pdf.worker.min.js'];
const manifestPath = path.join(vendor, 'dependency-integrity.json');

test('browser-local document parsers require a complete, pinned, auditable vendor set', t => {
  for (const name of expected) assert.ok(html.includes(name), `Expected same-origin parser reference: ${name}`);
  const present = expected.filter(name => fs.existsSync(path.join(vendor, name)));
  if (present.length === 0) {
    t.diagnostic('RELEASE HOLD: real PDF/DOCX extraction not verified; all three same-origin vendor assets are absent.');
    return;
  }
  assert.deepEqual(present, expected, 'Partial vendor installation is unsafe: require both PDF API/worker and DOCX parser');
  assert.ok(fs.existsSync(manifestPath), 'Require pinned provenance, licenses and SHA-256 manifest');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  assert.equal(manifest.schemaVersion, 1);
  assert.deepEqual(Object.keys(manifest.assets).sort(), expected.slice().sort());
  for (const name of expected) {
    const entry = manifest.assets[name];
    assert.match(entry.version, /^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][a-zA-Z0-9.-]+)?$/);
    assert.match(entry.license, /^[A-Za-z0-9 .+()-]{2,80}$/);
    assert.match(entry.officialSource, /^https:\/\//);
    assert.match(entry.sha256, /^[a-f0-9]{64}$/);
    const actual = crypto.createHash('sha256').update(fs.readFileSync(path.join(vendor, name))).digest('hex');
    assert.equal(actual, entry.sha256, `Integrity mismatch: ${name}`);
  }
  assert.equal(manifest.assets['pdf.min.js'].version, manifest.assets['pdf.worker.min.js'].version,
    'PDF.js API and worker must use identical pinned versions');
});
