"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const read = (name) => JSON.parse(fs.readFileSync(path.join(__dirname, "../data/catalog-evidence", name), "utf8"));
const data = read("qcc-nursing-cross-office-2026-10-31.v1.json");
const state = read("qcc-nursing-nysed-registration-2026-10-31.v1.json");
const catalog = read("qcc-nursing-2026-2027.v1.json");

test("dated evidence remains review-only and does not rewrite the NYSED record", () => {
  assert.equal(data.verified_local_date, "2026-10-31");
  assert.equal(data.publication_status, "review_only_not_integrated_into_live_matcher");
  assert.equal(data.institution.unitid, state.institution.unitid);
  assert.equal(data.institution.cip2020, catalog.classification.cip2020);
  assert.deepEqual(state.verification.independent_state_page_institution_name_visible_for_codes, ["01513"]);
});

test("four cross-office codes match QCC catalog and historical NYSED details exactly", () => {
  assert.equal(data.cross_office_code_matches.length, 4);
  const found = data.cross_office_code_matches.map(x => [x.plan, x.code]).sort();
  assert.deepEqual(found, state.state_registry_records.map(x => [x.plan, x.code]).sort());
  assert.deepEqual(found, catalog.catalog.plans.map(x => [x.code, x.nysed_program_code]).sort());
  assert.equal(new Set(data.cross_office_code_matches.map(x => x.code)).size, 4);
});

test("three dual/joint pathways retain named partners and distinct source labels", () => {
  const expected = new Map([
    ["34693", /Hunter.Bellevue/i], ["36043", /York/i], ["37062", /Professional Studies/i]
  ]);
  for (const [code, partner] of expected) {
    const row = data.cross_office_code_matches.find(x => x.code === code);
    assert.match(row.perkins_label, partner);
    assert.match(row.nursing_department_label, partner);
    assert.match(row.perkins_label, /AAS\/BS/);
    assert.equal(row.hegis_as_printed, "5208.10");
  }
});

test("printed standard nursing HEGIS is not silently normalized to a CIP", () => {
  const standard = data.cross_office_code_matches.find(x => x.code === "01513");
  assert.equal(standard.hegis_as_printed, "5208.1");
  assert.equal(data.institution.cip2020, "51.3801");
  assert.equal(data.verification.hegis_is_cip2020, false);
});

test("2023–24 Perkins labels cannot become current funding or individual eligibility", () => {
  assert.equal(data.verification.perkins_table_year, "2023-2024");
  assert.ok(data.cross_office_code_matches.every(x => x.perkins_funded_as_printed === "Yes"));
  assert.equal(data.verification.current_perkins_funding_verified, false);
  assert.equal(data.verification.student_perkins_eligibility_verified, false);
  assert.equal(data.verification.current_catalog_availability_inferred_from_perkins, false);
  assert.match(data.sources[0].scope, /NOT proof of 2026/);
});

test("cross-office school corroboration does not claim independent state institution binding", () => {
  assert.equal(data.verification.four_codes_matched_between_two_qcc_offices, true);
  assert.equal(data.verification.cross_office_corroboration_not_independent_state_registration, true);
  assert.equal(data.verification.independent_state_institution_binding_for_three_dual_codes_verified, false);
  for (const code of ["34693", "36043", "37062"]) {
    assert.equal(state.state_registry_records.find(x => x.code === code).extraction_header, "not_in_extracted_page_body");
  }
});

test("all evidence URLs use first-party QCC domains and licensure boundaries remain explicit", () => {
  assert.equal(data.sources.length, 3);
  for (const src of data.sources) {
    const u = new URL(src.url);
    assert.ok(u.hostname === "www.qcc.cuny.edu" || u.hostname === "qcc.catalog.cuny.edu");
  }
  assert.equal(data.verification.individual_nursing_licensure_verified, false);
  assert.equal(data.verification.conditional_bachelors_guaranteed, false);
  assert.match(data.limitations.join(" "), /not two independent state registration records/);
});
