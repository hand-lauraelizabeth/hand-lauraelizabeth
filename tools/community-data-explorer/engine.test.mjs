import assert from "node:assert/strict";
import test from "node:test";
import {createHash,webcrypto} from "node:crypto";
import {MAX_BYTES,parseCsv,normalizeRows,readCsvBytes,fingerprintCsv,compareRecords,evidenceExport} from "./engine.mjs";
const header = "source_id,geography,variable,series,period_start,period_end,estimate,moe";
const a = '0001,"New York, NY",B19013_001E,acs5,2015,2019,60000,1000';
const b = '0002,"New York, NY",B19013_001E,acs5,2020,2024,70000,1200';
const c = '0003,"Other, NY",B19013_001E,acs5,2020,2024,,*****';
const csv = [header,a,b,c].join("\r\n");
const bytes = s => new TextEncoder().encode(s).buffer;
test("strict CSV quoting, BOM, CRLF, embedded newlines", () => {
  assert.equal(parseCsv('\uFEFFa,b\r\n"line\n2","a""b"\r\n')[1][0],"line\n2");
  assert.equal(parseCsv('a,b\r\n"line\n2","a""b"\r\n')[1][1],'a"b');
  assert.throws(()=>parseCsv('a\n"unfinished'),/Unclosed/);
  assert.throws(()=>parseCsv('a\n"ok"junk'),/quoting/);
});
test("exact IDs, missing data, no silent transformation", () => {
  const r = readCsvBytes(bytes(csv),bytes(csv).byteLength);
  assert.deepEqual(r.map(x=>x.source_id),["0001","0002","0003"]);
  assert.equal(r[0].geography,"New York, NY");
  assert.equal(r[2].estimate,null); assert.equal(r[2].moe,null);
  assert.equal(r[2].moe_raw,"*****");
  assert.equal(evidenceExport(r,"Synthetic example").provenance_status,"user-supplied; not independently verified");
});
test("comparison gates overlapping ACS5, different series, geography, missing", () => {
  const r = normalizeRows(parseCsv(csv));
  assert.equal(compareRecords(r,"0001","0002").difference,10000);
  assert.equal(compareRecords(r,"0002","0003").comparable,false);
  assert.equal(compareRecords(r,"0001","0003").comparable,false);
  assert.equal(compareRecords(r,"0002","0003").difference,null);
  assert.throws(()=>compareRecords(r,"0001","0001"),/different/);
  const overlap = normalizeRows(parseCsv([header,a,a.replace("0001","0004").replace("2015,2019","2016,2020")].join("\n")));
  assert.equal(compareRecords(overlap,"0001","0004").comparable,false);
});
test("reject malformed, duplicate, unsafe and inconsistent inputs", () => {
  const bad = [
    [header,a,a].join("\n"),
    [header,a.replace("0001","\u202e0001"),
    [header,a.replace("0001","=1+1")].join("\n"),
    [header,a.replace("0001","  +SUM(1)")].join("\n")].join("\n"),
    [header,a.replace("2015,2019","2019,2022")].join("\n"),
    [header,a.replace("acs5","acs1")].join("\n"),
    [header,a.replace("60000","=1+1")].join("\n"),
    [header,a.replace("1000","-3")].join("\n"),
    [header,a.replace("B19013_001E","B19013_001M")].join("\n"),
    [header,a.replace("60000","9007199254740992")].join("\n"),
    [header,a+",extra"].join("\n"),
    [header,a.replace("0001","")].join("\n")
  ];
  for(const item of bad) assert.throws(()=>normalizeRows(parseCsv(item)));
  assert.throws(()=>readCsvBytes(bytes(csv),1),/size/);
  assert.throws(()=>readCsvBytes(new Uint8Array([255]).buffer,1),/UTF-8/);
  assert.throws(()=>readCsvBytes(new ArrayBuffer(MAX_BYTES+1),MAX_BYTES+1),/size/);
  assert.throws(()=>parseCsv("a\0b"),/NUL/);
});
test("property checks: exact zero-padded IDs and deterministic comparisons", () => {
  for(let i=0;i<200;i++){
    const id1="A"+String(i).padStart(5,"0"),id2="B"+String(i).padStart(5,"0");
    const one=String(2000+i),two=String(2100+i);
    const r=normalizeRows(parseCsv([header,
      [id1,"Place", "B19013_001E","acs5",2015,2019,one,100].join(","),
      [id2,"Place", "B19013_001E","acs5",2020,2024,two,120].join(",")].join("\n")));
    assert.equal(r[0].source_id,id1);
    assert.equal(compareRecords(r,id1,id2).difference,100);
  }
});

test("local SHA-256 fingerprints match independent Node crypto oracle", async () => {
  for(let i=0;i<80;i++) {
    const value = "synthetic CSV payload "+i+"\n"+String(i).padStart(6,"0");
    const buffer = bytes(value);
    const actual = await fingerprintCsv(buffer,webcrypto);
    const expected = createHash("sha256").update(new Uint8Array(buffer)).digest("hex");
    assert.equal(actual.sha256,expected);
    assert.equal(actual.byte_count,buffer.byteLength);
    assert.match(actual.verification,/authenticity not verified/);
  }
  const fallback = await fingerprintCsv(bytes("offline"),null);
  assert.equal(fallback.sha256,null);
  assert.match(fallback.verification,/unavailable/);
  await assert.rejects(fingerprintCsv(new ArrayBuffer(MAX_BYTES+1),webcrypto),/oversized/);
});
