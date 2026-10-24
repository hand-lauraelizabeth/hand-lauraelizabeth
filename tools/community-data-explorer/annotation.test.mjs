import assert from "node:assert/strict";
import test from "node:test";
import {normalizeRows,parseCsv,compareRecords,evidenceExport} from "./engine.mjs";

const header = "source_id,geography,variable,series,period_start,period_end,estimate,moe";
function rows(estimate="37.4",moe="0.3",secondEstimate="38.1",secondMoe="0.4") {
  return normalizeRows(parseCsv([
    header,
    ["00001","Synthetic place","B01002_001E","acs5",2015,2019,estimate,moe].join(","),
    ["00002","Synthetic place","B01002_001E","acs5",2020,2024,secondEstimate,secondMoe].join(",")
  ].join("\n")));
}
test("all documented numeric annotation codes preserve raw strings and distinguish status", () => {
  const cases = [
    ["-999999999","suppressed_insufficient_cases"],
    ["-888888888.0","not_applicable"],
    ["-666666666.00","insufficient_observations"],
    ["-555555555.00","controlled_moe"],
    ["-333333333.0","open_interval_moe"],
    ["-222222222","insufficient_moe"]
  ];
  for (const [raw,status] of cases) {
    const r = rows("37.4",raw)[0];
    assert.equal(r.moe,null,raw);
    assert.equal(r.moe_status,status,raw);
    assert.equal(r.moe_raw,raw);
    assert.equal(r.source_id,"00001");
  }
});
test("estimate-only sentinels, text annotations and missing are explicit", () => {
  for (const [raw,status] of [
    ["-999999999","suppressed_insufficient_cases"],
    ["-888888888.00","not_applicable"],
    ["-666666666","insufficient_observations"],
    ["N","suppressed_insufficient_cases"],["(X)","not_applicable"],
    ["-","insufficient_observations"],["","missing"],["null","missing"]
  ]) {
    const r = rows(raw,"0.3")[0];
    assert.equal(r.estimate,null,raw);
    assert.equal(r.estimate_status,status,raw);
    assert.equal(r.estimate_raw,raw);
  }
  for (const [raw,status] of [["**","insufficient_moe"],["***","open_interval_moe"],
    ["*****","controlled_moe"],["N","suppressed_insufficient_cases"],
    ["(X)","not_applicable"],["","missing"],["null","missing"]]) {
    const r = rows("37.4",raw)[0];
    assert.equal(r.moe_status,status,raw);
    assert.equal(r.moe,null,raw);
  }
});
test("controlled MOE is not silently converted to zero; arithmetic remains explicitly noninferential", () => {
  const r = rows("37.4","-555555555.00");
  const result = compareRecords(r,"00001","00002");
  assert.equal(result.comparable,true);
  assert.equal(result.difference_exact,"0.7");
  assert.ok(result.cautions.some(c=>c.includes("controlled_moe") && c.includes("not a numeric zero")));
  assert.ok(result.cautions.some(c=>c.includes("no statistical significance determination")));
  const exported = JSON.parse(JSON.stringify(evidenceExport(r,"Synthetic only",result)));
  assert.equal(exported.records[0].moe_raw,"-555555555.00");
  assert.equal(exported.records[0].moe_status,"controlled_moe");
  assert.equal(exported.records[0].moe,null);
  assert.equal(exported.records[0].source_id,"00001");
  assert.equal(exported.comparison.difference_exact,"0.7");
});
test("unsupported annotation codes, wrong field semantics and malformed numeric inputs fail closed", () => {
  for (const raw of ["-777777777","-555555555.000","-555555555.1","***","*****","**",
    "-222222222","-333333333","-555555555","NaN","-1"]) {
    assert.throws(()=>rows(raw,"0.3"),undefined,raw);
  }
  for (const raw of ["-777777777","-222222222.000","-222222222.1","=SUM(1)","-1","-999999999.000"]) {
    assert.throws(()=>rows("37.4",raw),undefined,raw);
  }
});
