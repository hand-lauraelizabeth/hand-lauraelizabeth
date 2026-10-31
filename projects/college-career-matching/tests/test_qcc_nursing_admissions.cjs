"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const evidence = JSON.parse(fs.readFileSync(path.join(__dirname,"../data/catalog-evidence/qcc-nursing-admissions-2026-10-30.v1.json"),"utf8"));
const catalog = JSON.parse(fs.readFileSync(path.join(__dirname,"../data/catalog-evidence/qcc-nursing-2026-2027.v1.json"),"utf8"));

test("operational snapshot is dated, first-party, and bounded", () => {
  assert.equal(evidence.verified_local_date,"2026-10-30");
  assert.equal(evidence.institution.unitid,catalog.institution.unitid);
  assert.equal(evidence.institution.cip2020,catalog.classification.cip2020);
  assert.match(evidence.scope,/not a real-time application/);
  for (const url of Object.values(evidence.sources)) {
    assert.ok(["www.qcc.cuny.edu","qcc.catalog.cuny.edu"].includes(new URL(url).hostname));
  }
});
test("all four school plan codes are independently corroborated by school, not state", () => {
  const original = catalog.catalog.plans.map(p=>[p.code,p.nysed_program_code]).sort();
  const crosscheck = evidence.crosschecked_plan_codes.map(p=>[p.plan,p.school_reported_nysed_code]).sort();
  assert.deepEqual(crosscheck,original);
  assert.match(evidence.plan_code_verification,/not by an NYSED registration database/);
  assert.equal(catalog.licensure.nysed_program_code_independently_verified,false);
});
test("NEX operational evidence cannot silently erase RN PAX contradiction", () => {
  assert.equal(evidence.exam_evidence.current_department_page,"NEX");
  assert.equal(evidence.exam_evidence.prospective_department_page,"NEX");
  assert.equal(evidence.exam_evidence.catalog_application_section,"NEX");
  assert.equal(evidence.exam_evidence.catalog_admission_section,"RN PAX");
  assert.equal(evidence.exam_evidence.authoritative_resolution,false);
  assert.deepEqual(catalog.admissions.college_catalog_exam_mentions,["NEX","RN PAX"]);
  assert.match(evidence.exam_evidence.operational_preference,/direct confirmation/);
});
test("spring 2027 clinical application window is elapsed, not universal closure", () => {
  const w = evidence.spring_2027_clinical_application;
  assert.equal(w.announced_open_date,"2026-10-05");
  assert.equal(w.announced_close_date,"2026-10-16");
  assert.ok(Date.parse(w.announced_close_date)<Date.parse(evidence.verified_local_date));
  assert.equal(w.college_general_admissions_distinct,true);
  assert.equal(w.no_current_seat_claim,true);
  assert.match(w.status_as_of_verification,/not verified/);
});
test("conflicting exam fee estimates remain non-authoritative", () => {
  const p = evidence.published_exam_price_conflict;
  assert.equal(p.nursing_home_price_usd,80);
  assert.equal(p.prospective_page_prose_price_usd,80);
  assert.equal(p.prospective_page_estimated_fees_table_usd,68.5);
  assert.equal(p.price_verified_for_purchase,false);
  assert.match(p.guidance,/before payment/);
});
test("licensure, SAT\/ACT, and credential safety boundaries remain explicit", () => {
  const limitations=evidence.limitations.join(" ");
  assert.match(limitations,/not four federal CIP codes/);
  assert.match(limitations,/not an RN license/);
  assert.match(limitations,/SAT\/ACT/);
  assert.match(limitations,/not NYSED registration-code confirmation/);
});
