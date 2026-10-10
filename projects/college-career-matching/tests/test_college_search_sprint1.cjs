"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// Test the shipped script, not a second implementation of its filter logic.
const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "college-search-sprint1.html"), "utf8");
const script = html.match(/<script data-college-search>([\s\S]*?)<\/script>/);
assert.ok(script, "Missing component script");
const context = { window: {}, document: { getElementById: () => null } };
vm.runInNewContext(script[1], context, { filename: "college-search-sprint1.html" });
const core = context.window.CollegeSearchCore;
assert.ok(core, "Missing testable core");
const payload = JSON.parse(fs.readFileSync(
  path.join(root, "data", "sprint1", "college-search-national.v1.json"), "utf8"
));
const records = core.validatePayload(payload);
const originalOrder = Array.from(records, r => r.unitid);

test("national source has 6,243 unique UNITIDs and 59 state codes", () => {
  assert.equal(records.length, 6243);
  assert.equal(new Set(records.map(r => r.unitid)).size, 6243);
  assert.equal(new Set(records.map(r => r.state)).size, 59);
});

test("name search handles case, whitespace and partial names", () => {
  const found = core.filterSchools(records, { name: "  hARVard uNIVERSITY  ", state: "", sort: "name-asc" });
  assert.equal(found.length, 1);
  assert.equal(found[0].unitid, "166027");
  const partial = core.filterSchools(records, { name: "Columbia", state: "", sort: "name-asc" });
  assert.ok(partial.length >= 3);
  assert.ok(partial.every(r => r.name.toLowerCase().includes("columbia")));
});

test("state filter yields verified NY, CA and PR totals", () => {
  for (const [state, expected] of [["NY", 417], ["CA", 658], ["PR", 138]]) {
    const found = core.filterSchools(records, { name: "", state, sort: "name-asc" });
    assert.equal(found.length, expected, state);
    assert.ok(found.every(r => r.state === state));
  }
});

test("combined filters intersect name and state", () => {
  const columbia = core.filterSchools(records, { name: "Columbia", state: "NY", sort: "name-asc" });
  assert.equal(columbia.length, 3);
  assert.ok(columbia.every(r => r.state === "NY" && r.name.includes("Columbia")));
  const harvard = core.filterSchools(records, { name: "Harvard University", state: "MA", sort: "name-asc" });
  assert.equal(harvard.length, 1);
  assert.equal(harvard[0].unitid, "166027");
});

test("A-Z and Z-A sorting reverse the same subset without mutating input", () => {
  const base = { name: "University of California-", state: "CA" };
  const ascending = core.filterSchools(records, { ...base, sort: "name-asc" });
  const descending = core.filterSchools(records, { ...base, sort: "name-desc" });
  assert.equal(ascending.length, 10);
  assert.equal(ascending[0].name, "University of California-Berkeley");
  assert.equal(descending[0].name, "University of California-Santa Cruz");
  assert.deepEqual(Array.from(ascending, r => r.unitid),
    Array.from(descending, r => r.unitid).reverse());
  assert.deepEqual(Array.from(records, r => r.unitid), originalOrder);
});

test("unmatched and contradictory filters return zero results", () => {
  assert.equal(core.filterSchools(records, { name: "NO SUCH COLLEGE 12345", state: "", sort: "name-asc" }).length, 0);
  assert.equal(core.filterSchools(records, { name: "Harvard University", state: "NY", sort: "name-asc" }).length, 0);
});

test("Clear resets all three controls, invokes filtering and restores name focus", () => {
  // Isolate the shipped Clear handler with lightweight control stubs.
  const clearFunction = html.match(/\bfunction clear\(\) \{([\s\S]*?)\n  \}/);
  assert.ok(clearFunction, "Missing Clear handler");
  let focused = false, reapplied = 0;
  const nameInput = { value: "Harvard University", focus() { focused = true; } };
  const stateSelect = { value: "MA" };
  const sortSelect = { value: "name-desc" };
  const scope = { nameInput, stateSelect, sortSelect, resetFilterOptions: core.resetFilterOptions, applyFilters() { reapplied++; } };
  vm.runInNewContext("function clear() {" + clearFunction[1] + "\n}\nclear();", scope);
  assert.equal(nameInput.value, "");
  assert.equal(stateSelect.value, "");
  assert.equal(sortSelect.value, "name-asc");
  assert.equal(reapplied, 1);
  assert.equal(focused, true);
  assert.equal(core.filterSchools(records, { name: nameInput.value, state: stateSelect.value, sort: sortSelect.value }).length, 6243);
});

test("incomplete or malformed national data is rejected", () => {
  assert.throws(() => core.validatePayload(null), /unexpected format/);
  assert.throws(() => core.validatePayload({ ...payload, institutions: {} }), /incomplete/);
});
