"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const base = path.join(__dirname, "../data/programs/ipeds2025");
function readJson(file) {
  const raw = fs.readFileSync(path.join(base, file));
  return {raw, data: JSON.parse(raw.toString("utf8"))};
}
function sha256(raw) {
  return crypto.createHash("sha256").update(raw).digest("hex");
}
test("all 13 historical program shards satisfy pinned manifest bytes, hashes and row counts", () => {
  const manifest = readJson("programs.manifest.v1.json").data;
  assert.equal(manifest.shards.length, 13);
  assert.equal(manifest.current_program_offering_verified, false);
  let rows = 0, institutions = 0;
  const ids = new Set();
  for (const shard of manifest.shards) {
    const {raw, data} = readJson(shard.file);
    assert.equal(raw.length, shard.bytes, shard.file);
    assert.equal(sha256(raw), shard.sha256, shard.file);
    assert.equal(data.institutions.length, shard.institutions, shard.file);
    const n = data.institutions.reduce((sum, [id, records]) => {
      assert.match(id, /^\d{6}$/);
      assert.equal(ids.has(id), false, "duplicate institutional ID " + id);
      ids.add(id);
      return sum + records.length;
    }, 0);
    assert.equal(n, shard.program_award_records, shard.file);
    rows += n;
    institutions += data.institutions.length;
  }
  assert.equal(rows, manifest.counts.joined_program_award_records);
  assert.equal(rows, 235330);
  assert.equal(institutions, 5658);
  assert.equal(ids.size, institutions);
});
test("real rows distinguish positive and zero historical awards without reserved CIP or short certificates", () => {
  const manifest = readJson("programs.manifest.v1.json").data;
  const titles = readJson(manifest.cip2020_titles.file).data;
  const reserved = new Set(Object.keys(titles).filter(code => /\breserved\b/i.test(titles[code])));
  assert.equal(Object.keys(titles).length, 2325);
  assert.equal(reserved.size, 30);
  const observed = new Set(), positive = new Set(), zero = new Set();
  let positiveRows = 0, zeroRows = 0;
  for (const shard of manifest.shards) {
    const {data} = readJson(shard.file);
    for (const [, records] of data.institutions) {
      for (const [cip, level, count, status] of records) {
        assert.ok(Object.hasOwn(titles, cip), "unknown CIP " + cip);
        assert.equal(reserved.has(cip), false, "reserved CIP " + cip);
        assert.notEqual(level, "1");
        assert.notEqual(level, "20");
        assert.notEqual(level, "21");
        assert.equal(status, "reported");
        assert.ok(Number.isInteger(count) && count >= 0);
        observed.add(cip);
        if (count > 0) { positive.add(cip); positiveRows++; }
        else { zero.add(cip); zeroRows++; }
      }
    }
  }
  assert.equal(observed.size, 1591);
  assert.equal(positive.size, 1551);
  assert.equal([...zero].filter(code => !positive.has(code)).length, 40);
  assert.equal(positiveRows, 175342);
  assert.equal(zeroRows, 59988);
});
