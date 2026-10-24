import assert from "node:assert/strict";
import test from "node:test";
import {normalizeRows,parseCsv,compareRecords,evidenceExport} from "./engine.mjs";

const header = "source_id,geography,variable,series,period_start,period_end,estimate,moe";
function csv(a,b,moeA="0.3",moeB="0.4") {
  return [header,
    ["00001","Place","B01002_001E","acs5","2015","2019",a,moeA].join(","),
    ["00002","Place","B01002_001E","acs5","2020","2024",b,moeB].join(",")
  ].join("\n");
}
test("ACS median age decimals, exact IDs and margins survive JSON evidence export", () => {
  const rows = normalizeRows(parseCsv(csv("37.4","38.1")));
  assert.equal(rows[0].estimate,37.4);
  assert.equal(rows[0].moe,0.3);
  assert.equal(rows[0].moe_raw,"0.3");
  const result = compareRecords(rows,"00001","00002");
  assert.equal(result.difference_exact,"0.7");
  assert.equal(result.difference,0.7);
  const evidence = evidenceExport(rows,"Synthetic median age",result);
  assert.equal(evidence.records[0].source_id,"00001");
  assert.equal(evidence.records[0].estimate_raw,"37.4");
  assert.equal(evidence.comparison.difference_exact,"0.7");
});
test("exact decimal subtraction handles sign, zero and trailing zeroes", () => {
  for (const [a,b,expected] of [["0.3","0.1","-0.2"],["12.000","12.100","0.1"],
      ["100000","100000.000001","0.000001"],["0","0","0"],
      ["9007199254740991","9007199254740990","-1"]]) {
    const rows = normalizeRows(parseCsv(csv(a,b)));
    assert.equal(compareRecords(rows,"00001","00002").difference_exact,expected);
  }
});
test("unsupported numeric syntax and unsafe precision fail closed", () => {
  for (const bad of ["1e3","-1","0.1234567","01.2","1000000000001.1",
      "9007199254740992","NaN","Infinity","+4","=1+1"])
    assert.throws(() => normalizeRows(parseCsv(csv(bad,"1"))));
});
test("missing values remain missing and block arithmetic", () => {
  const rows = normalizeRows(parseCsv(csv("","*****","","-666666666")));
  assert.equal(rows[0].estimate,null);
  assert.equal(rows[1].estimate,null);
  assert.equal(rows[0].moe,null);
  assert.equal(rows[1].moe,null);
  const result = compareRecords(rows,"00001","00002");
  assert.equal(result.comparable,false);
  assert.equal(result.difference_exact,null);
});
