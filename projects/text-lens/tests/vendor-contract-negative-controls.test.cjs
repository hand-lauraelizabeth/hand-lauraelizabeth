'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const contract = path.join(__dirname, 'vendor-contract.test.cjs');
const names = ['mammoth.browser.min.js', 'pdf.min.js', 'pdf.worker.min.js'];
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function exercise(change) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ft11-vendor-contract-'));
  try {
    fs.mkdirSync(path.join(dir, 'tests'));
    fs.mkdirSync(path.join(dir, 'vendor'));
    fs.copyFileSync(contract, path.join(dir, 'tests', 'vendor-contract.test.cjs'));
    fs.writeFileSync(path.join(dir, 'text-lens.html'), names.join('\n'));
    const assets = {};
    for (const name of names) {
      const bytes = Buffer.from('synthetic fixture for ' + name);
      fs.writeFileSync(path.join(dir, 'vendor', name), bytes);
      assets[name] = {
        version: '3.1.2', license: 'BSD-3-Clause',
        officialSource: 'https://example.org/synthetic-fixture',
        sha256: sha(bytes)
      };
    }
    const manifest = { schemaVersion: 1, assets };
    change(dir, manifest);
    fs.writeFileSync(path.join(dir, 'vendor', 'dependency-integrity.json'), JSON.stringify(manifest));
    const result = spawnSync(process.execPath, ['--test', path.join(dir, 'tests', 'vendor-contract.test.cjs')], {
      encoding: 'utf8', timeout: 15000
    });
    assert.equal(result.error, undefined, String(result.error));
    return { status: result.status, output: result.stdout + result.stderr };
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

test('complete synthetic vendor set passes integrity contract', () => {
  const result = exercise(() => {});
  assert.equal(result.status, 0, result.output);
});

test('modified vendor bytes fail SHA-256 verification', () => {
  const result = exercise(dir => fs.appendFileSync(path.join(dir, 'vendor', 'pdf.min.js'), 'tampered'));
  assert.notEqual(result.status, 0, result.output);
  assert.match(result.output, /Integrity mismatch: pdf\.min\.js/);
});

test('mismatched PDF API and worker versions fail', () => {
  const result = exercise((dir, manifest) => { manifest.assets['pdf.worker.min.js'].version = '3.1.3'; });
  assert.notEqual(result.status, 0, result.output);
  assert.match(result.output, /identical pinned versions/);
});

test('missing parser asset fails even when manifest lists it', () => {
  const result = exercise(dir => fs.unlinkSync(path.join(dir, 'vendor', 'mammoth.browser.min.js')));
  assert.notEqual(result.status, 0, result.output);
  assert.match(result.output, /Partial vendor installation is unsafe/);
});
