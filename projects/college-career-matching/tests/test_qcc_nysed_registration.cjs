"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const data = JSON.parse(fs.readFileSync(path.join(__dirname,"../data/catalog-evidence/qcc-nursing-nysed-registration-2026-10-31.v1.json"),"utf8"));
const catalog = JSON.parse(fs.readFileSync(path.join(__dirname,"../data/catalog-evidence/qcc-nursing-2026-2027.v1.json"),"utf8"));
const prior = JSON.parse(fs.readFileSync(path.join(__dirname,"../data/catalog-evidence/qcc-nursing-admissions-2026-10-30.v1.json"),"utf8"));
test("dated state evidence follows school-only evidence without rewriting its history",()=>{
  assert.equal(data.verified_local_date,"2026-10-31");
  assert.equal(prior.verified_local_date,"2026-10-30");
  assert.equal(prior.crosschecked_plan_codes.length,4);
  assert.equal(data.publication_status,"review_only_not_integrated_into_live_matcher");
  assert.equal(catalog.licensure.nysed_program_code_independently_verified,false);
});
test("all four state code URLs are exact and distinct",()=>{
  assert.equal(data.state_registry_records.length,4);
  const codes = data.state_registry_records.map(x=>x.code);
  assert.equal(new Set(codes).size,4);
  for(const x of data.state_registry_records){
    const u = new URL(x.official_state_record_url);
    assert.equal(u.hostname,"www2.nysed.gov");
    assert.equal(u.pathname,"/COMS/RP090/IRPSL3");
    assert.equal(u.searchParams.get("PROGCD"),x.code);
  }
});
test("state program codes match QCC plans without inventing new CIPs",()=>{
  assert.equal(data.institution.unitid,catalog.institution.unitid);
  assert.equal(data.institution.cip2020,catalog.classification.cip2020);
  const observed = data.state_registry_records.map(x=>[x.plan,x.code]).sort();
  const expected = catalog.catalog.plans.map(x=>[x.code,x.nysed_program_code]).sort();
  assert.deepEqual(observed,expected);
});
test("standard nursing AAS state detail carries historic RN LIC QUAL, not license issuance",()=>{
  const x=data.state_registry_records.find(x=>x.code==="01513");
  assert.deepEqual(x.awards,[{award:"AAS",lic_qual:"RN",first_registration:"09/1967",last_registration_action:"08/2023"}]);
  assert.equal(x.extraction_header,"institution_name_and_program_title_visible");
  assert.equal(data.verification.individual_license_or_nclex_eligibility_verified,false);
});
test("each dual/joint code has distinct AAS RN qualifier and BS NONE qualifier",()=>{
  for(const code of ["34693","36043","37062"]){
    const x=data.state_registry_records.find(x=>x.code===code);
    assert.equal(x.awards.length,2);
    assert.deepEqual(x.awards.map(a=>[a.award,a.lic_qual]),[["AAS","RN"],["BS","NONE"]]);
    assert.equal(x.extraction_header,"not_in_extracted_page_body");
  }
  assert.equal(data.verification.conditional_bachelors_award_guaranteed,false);
});
test("state evidence does not assert independent college binding for missing headers",()=>{
  assert.deepEqual(data.verification.independent_state_page_institution_name_visible_for_codes,["01513"]);
  assert.equal(data.verification.other_three_school_association_requires_institution_level_registry_confirmation,true);
  assert.match(data.limitations.join(" "),/School-to-code mapping comes from QCC/);
});
test("historic registration actions never imply current availability, licensure, or accreditation",()=>{
  const v=data.verification;
  assert.equal(v.exact_state_registration_action_dates_not_current_status,true);
  assert.equal(v.professional_accreditation_current_status_verified,false);
  assert.equal(v.admissions_seats_exam_or_fee_verified,false);
  assert.equal(v.individual_license_or_nclex_eligibility_verified,false);
  assert.match(v.scope,/not current admission availability/);
});
