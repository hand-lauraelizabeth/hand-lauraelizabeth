"use strict";
// Unit tests exercise the exact plain-JS functions embedded in the public component.
// Node's built-in test runner is used; no npm install or test dependencies.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "..", "college-search-sprint1.html"), "utf8");
const match = html.match(/<script data-college-search>([\s\S]*?)<\/script>/);
assert.ok(match, "Could not locate the production College Search JavaScript");

const browser = {};
const context = {
  window: browser,
  document: { getElementById: () => null }, // prevents the UI bootstrapping
  Intl,
};
vm.runInNewContext(match[1], context, { filename: "college-search-sprint1.js", timeout: 1000 });
const core = browser.CollegeSearchCore;
assert.ok(core && typeof core.filterSchools === "function");
assert.equal(typeof core.resetFilterOptions, "function");

const records = [
  { unitid: "100001", name: "Alpha College", city: "Albany", state: "NY", url: null },
  { unitid: "100002", name: "Alpha College", city: "Los Angeles", state: "CA", url: null },
  { unitid: "100003", name: "Zeta University", city: "New York", state: "NY", url: null },
  { unitid: "100004", name: "Café University", city: "Berkeley", state: "CA", url: null },
  { unitid: "100005", name: "Beta School", city: "Austin", state: "TX", url: null },
  { unitid: "100006", name: "Beta Institute", city: "Ithaca", state: "NY", url: null },
];
const ids = (results) => Array.from(results, school => school.unitid);
const filtered = (options) => core.filterSchools(records, options);

test("school name filters case-insensitively and does not search city", () => {
  assert.deepEqual(ids(filtered({ name: " aLpHa ", state: "", sort: "name-asc" })), ["100001", "100002"]);
  assert.deepEqual(ids(filtered({ name: "Ithaca", state: "", sort: "name-asc" })), []);
});

test("name search is Unicode accent-insensitive", () => {
  assert.deepEqual(ids(filtered({ name: "cafe", state: "", sort: "name-asc" })), ["100004"]);
});

test("state filters by exact postal code", () => {
  assert.deepEqual(
    ids(filtered({ name: "", state: "NY", sort: "name-asc" })),
    ["100001", "100006", "100003"]
  );
});

test("name and state filters are combined with AND", () => {
  assert.deepEqual(
    ids(filtered({ name: "college", state: "CA", sort: "name-asc" })),
    ["100002"]
  );
  assert.deepEqual(
    ids(filtered({ name: "college", state: "TX", sort: "name-asc" })),
    []
  );
});

test("sorting supports A-Z and Z-A with deterministic UNITID tie-breakers", () => {
  const asc = ids(filtered({ name: "", state: "", sort: "name-asc" }));
  const desc = ids(filtered({ name: "", state: "", sort: "name-desc" }));
  assert.deepEqual(asc, ["100001", "100002", "100006", "100005", "100004", "100003"]);
  assert.deepEqual(desc, ["100003", "100004", "100005", "100006", "100002", "100001"]);
  assert.deepEqual(ids(records), ["100001", "100002", "100003", "100004", "100005", "100006"],
    "Filtering must not mutate the original dataset");
});

test("zero-result search returns an empty list", () => {
  assert.deepEqual(
    ids(filtered({ name: "This institution does not exist", state: "NY", sort: "name-desc" })),
    []
  );
});

test("Clear resets name, state and sort to defaults and restores complete count", () => {
  const previous = { name: "Zeta", state: "NY", sort: "name-desc" };
  assert.equal(filtered(previous).length, 1);
  const defaults = core.resetFilterOptions();
  assert.equal(defaults.name, "");
  assert.equal(defaults.state, "");
  assert.equal(defaults.sort, "name-asc");
  assert.equal(filtered(defaults).length, records.length);
  assert.deepEqual(ids(filtered(defaults)), ["100001", "100002", "100006", "100005", "100004", "100003"]);
  assert.equal(previous.name, "Zeta", "Default reset does not secretly mutate state");
});

test("every reset returns independent default settings", () => {
  const a = core.resetFilterOptions();
  a.name = "modified";
  assert.equal(core.resetFilterOptions().name, "");
});
