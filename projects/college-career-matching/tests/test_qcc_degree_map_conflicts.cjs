"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.join(__dirname, "../data/catalog-evidence/");
const evidence = JSON.parse(fs.readFileSync(path.join(root, "qcc-nursing-degree-map-conflicts-2026-10-31.v1.json"), "utf8"));
const operational = JSON.parse(fs.readFileSync(path.join(root, "qcc-nursing-admissions-2026-10-30.v1.json"), "utf8"));
const catalog = JSON.parse(fs.readFileSync(path.join(root, "qcc-nursing-2026-2027.v1.json"), "utf8"));

function verifyUnresolved(e) {
  for (const key of ["nu101_repeat", "entrance_exam"]) {
    assert.equal(e.conflicts[key].status, "unresolved_first_party_conflict");
    assert.equal(e.conflicts[key].authoritative_resolution, false);
    assert.match(e.conflicts[key].public_guidance, /Confirm|confirm/);
  }
}
test("Dated 2026-27 first-party degree map is not a current-seat assertion", () => {
  assert.equal(evidence.verified_local_date, "2026-10-31");
  assert.equal(evidence.degree_map.catalog_year, "2026-2027");
  assert.equal(evidence.degree_map.total_required_credits, 65);
  assert.equal(evidence.degree_map.preclinical_credits_before_application, 13);
  assert.equal(evidence.degree_map.status, "listed_curriculum_not_live_seat_confirmation");
  assert.equal(evidence.institution.unitid, catalog.institution.unitid);
  assert.equal(evidence.institution.cip2020, catalog.classification.cip2020);
});
test("Every source is official QCC and the clinical source is distinct", () => {
  for (const [key, value] of Object.entries(evidence.sources)) {
    assert.ok(["www.qcc.cuny.edu", "qcc.catalog.cuny.edu"].includes(new URL(value).hostname), key);
  }
  assert.notEqual(evidence.sources.degree_map, evidence.sources.clinical_application);
  assert.notEqual(evidence.sources.general_college_admissions, evidence.sources.clinical_application);
});
test("NU-101 repeat exception and categorical no-repeat are not silently reconciled", () => {
  assert.match(evidence.degree_map.nu101_repeat, /Appeals Committee/);
  assert.match(evidence.clinical_application.nu101_repeat, /Unable to repeat/);
  assert.equal(evidence.conflicts.nu101_repeat.degree_map_position, "committee_approval_exception");
  assert.equal(evidence.conflicts.nu101_repeat.clinical_application_position, "categorical_no_repeat_after_withdrawal_or_below_C");
  verifyUnresolved(evidence);
});
test("RN PAX on degree map does not displace NEX clinical application", () => {
  assert.equal(evidence.degree_map.nu101_exam, "RN PAX");
  assert.equal(evidence.clinical_application.required_exam, "NEX");
  assert.equal(operational.exam_evidence.current_department_page, "NEX");
  assert.deepEqual(catalog.admissions.college_catalog_exam_mentions, ["NEX", "RN PAX"]);
  verifyUnresolved(evidence);
});
test("College admission dates are not clinical application deadlines", () => {
  assert.equal(evidence.general_admissions.term, "Spring 2027");
  assert.equal(evidence.general_admissions.freshman_deadline, "2027-01-25");
  assert.equal(evidence.general_admissions.transfer_readmit_deadline, "2027-01-29");
  assert.equal(evidence.clinical_application.spring_2027_open, "2026-10-05");
  assert.equal(evidence.clinical_application.spring_2027_close, "2026-10-16");
  assert.ok(evidence.clinical_application.spring_2027_close < evidence.verified_local_date);
  assert.equal(evidence.general_admissions.distinct_from_clinical_nursing_application, true);
  assert.equal(evidence.general_admissions.establishes_clinical_admission, false);
});
test("No seats, appeal entitlement, SAT/ACT policy, or licensure guarantee", () => {
  assert.equal(evidence.clinical_application.clinical_seat_guaranteed, false);
  assert.equal(evidence.clinical_application.late_exception_verified, false);
  const cautions = evidence.limitations.join(" ");
  assert.match(cautions, /NOT clinical Nursing deadlines/);
  assert.match(cautions, /SAT\/ACT/);
  assert.match(cautions, /RN\/LPN license/);
  assert.match(cautions, /individual NCLEX-RN/);
});
test("Adversarial mutation cannot manufacture authoritative resolution", () => {
  const fabricated = structuredClone(evidence);
  fabricated.conflicts.nu101_repeat.authoritative_resolution = true;
  assert.throws(() => verifyUnresolved(fabricated), /true !== false/);
  fabricated.conflicts.nu101_repeat.authoritative_resolution = false;
  fabricated.conflicts.entrance_exam.status = "resolved";
  assert.throws(() => verifyUnresolved(fabricated), /resolved/);
});
