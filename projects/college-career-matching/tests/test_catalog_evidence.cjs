"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const fixture = JSON.parse(fs.readFileSync(
  path.join(__dirname, "../data/catalog-evidence/qcc-nursing-2026-2027.v1.json"), "utf8"
));

test("Current catalog evidence is explicitly bounded and dated", () => {
  assert.equal(fixture.schema_version, "1.0");
  assert.match(fixture.verified_local_date, /^2026-10-30$/);
  assert.equal(fixture.institution.unitid, "190673");
  assert.equal(fixture.catalog.academic_year, "2026-2027");
  assert.equal(fixture.catalog.status, "listed_in_current_catalog_not_enrollment_confirmed");
  assert.match(fixture.evidence_scope, /NOT a live admission/);
});

test("One CIP maps to four distinct school plan codes, not four CIP classifications", () => {
  assert.equal(fixture.classification.cip6, "513801");
  assert.equal(fixture.classification.cip2020, "51.3801");
  const plans = fixture.catalog.plans;
  assert.equal(plans.length, 4);
  assert.deepEqual(plans.map(p => p.code).sort(), ["NH-AAS", "NPS-AAS", "NS-AAS", "NY-AAS"]);
  assert.equal(new Set(plans.map(p => p.nysed_program_code)).size, 4);
  assert.ok(plans.every(p => p.home_award === "A.A.S."));
});

test("Every school-specific program has its own first-party catalog link", () => {
  for (const plan of fixture.catalog.plans) {
    const u = new URL(plan.catalog_url);
    assert.equal(u.hostname, "qcc.catalog.cuny.edu");
    assert.ok(u.pathname.startsWith("/programs/" + plan.code));
  }
  assert.equal(fixture.catalog.plans.filter(p => p.additional_degree.startsWith("conditional B.S.")).length, 3);
  assert.equal(fixture.catalog.plans.filter(p => p.additional_degree === "none_asserted").length, 1);
});

test("Licensure and dual-degree limitations cannot be mistaken for guarantees", () => {
  assert.equal(fixture.licensure.license_eligibility_individually_verified, false);
  assert.equal(fixture.licensure.nysed_program_code_independently_verified, false);
  assert.equal(fixture.licensure.lpn_credential_inferred, false);
  assert.match(fixture.licensure.school_claim, /separate decisions/);
  assert.match(fixture.evidence_limitations.join(" "), /not automatic BSN awards/);
  assert.match(fixture.evidence_limitations.join(" "), /does not itself confer an RN license/);
});

test("Admissions testing contradiction is preserved rather than silently resolved", () => {
  assert.deepEqual(fixture.admissions.college_catalog_exam_mentions, ["NEX", "RN PAX"]);
  assert.match(fixture.admissions.exam_rule_status, /conflicting mentions/);
  assert.match(fixture.admissions.clinical_entry, /do not guarantee admission/);
  assert.match(fixture.evidence_limitations.join(" "), /No SAT\/ACT admission-policy conclusion/);
});

test("Sources distinguish direct catalog access from incomplete state-board readback", () => {
  assert.equal(new URL(fixture.licensure.school_claim_url).hostname, "qcc.catalog.cuny.edu");
  assert.equal(new URL(fixture.licensure.state_board_source).hostname, "www.op.nysed.gov");
  assert.match(fixture.licensure.state_board_source_access, /full page fetch returned 502/);
  assert.equal(new URL(fixture.institution.unitid_source).hostname, "carnegieclassifications.acenet.edu");
});
