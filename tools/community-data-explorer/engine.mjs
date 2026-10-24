// Browser-local ACS comparison engine. No network calls or spreadsheet CSV export.
export const MAX_BYTES = 2_000_000;
export const MAX_RECORDS = 5_000;
export const COLUMNS = ["source_id","geography","variable","series","period_start","period_end","estimate","moe"];
const dangerous = /[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]/u;
const formulaPrefix = /^[\s\u00a0]*[=+\-@\uff1d\uff0b\uff0d\uff20]/u;
const missingCodes = new Set(["-666666666","-888888888","-999999999"]);
function fail(message) { throw new Error(message); }
function safeLabel(value, field) {
  if (typeof value !== "string" || !value.trim() || value.length > 240 || dangerous.test(value) || formulaPrefix.test(value))
    fail(field + " must be nonempty, at most 240 characters, and free of control/directional/formula-prefix characters");
  return value; // Never trim exact source identifiers.
}
export function parseCsv(text) {
  if (typeof text !== "string" || text.includes("\0")) fail("CSV must be text without NUL bytes");
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
  const rows = []; let row = [], field = "", quoted = false, closed = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else { quoted = false; closed = true; }
      } else field += c;
    } else if (c === ",") { row.push(field); field = ""; closed = false; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = ""; closed = false;
      if (rows.length > MAX_RECORDS + 2) fail("CSV exceeds row limit");
    } else if (c === '"' && field === "" && !closed) quoted = true;
    else if (c === '"' || closed) fail("Invalid CSV quoting");
    else field += c;
  }
  if (quoted) fail("Unclosed CSV quoted field");
  if (field !== "" || row.length || (text.length && !/[\r\n]$/.test(text))) { row.push(field); rows.push(row); }
  if (rows.length && rows[rows.length - 1].length === 1 && rows[rows.length - 1][0] === "") rows.pop();
  return rows;
}
function integer(raw, field, allowMissing = false) {
  if (allowMissing && (raw === "" || raw === "*****" || missingCodes.has(raw))) return null;
  if (!/^(0|[1-9][0-9]*)$/.test(raw)) fail(field + " must be a nonnegative whole number or explicit missing code");
  const n = Number(raw);
  if (!Number.isSafeInteger(n)) fail(field + " exceeds safe integer range");
  return n;
}
export function normalizeRows(rows) {
  if (!Array.isArray(rows) || !rows.length || rows[0].length !== COLUMNS.length ||
      !COLUMNS.every((name, i) => rows[0][i] === name)) fail("Expected exact header: " + COLUMNS.join(","));
  if (rows.length < 2 || rows.length - 1 > MAX_RECORDS) fail("CSV requires 1 to " + MAX_RECORDS + " records");
  const seen = new Set();
  return rows.slice(1).map((cells, index) => {
    const line = index + 2;
    if (cells.length !== COLUMNS.length) fail("Row " + line + " has wrong column count");
    const [source_id,geography,variable,series,first,last,rawEstimate,rawMoe] = cells;
    safeLabel(source_id, "Row " + line + " source_id");
    safeLabel(geography, "Row " + line + " geography");
    if (!/^B[0-9]{5}_[0-9]{3}E$/.test(variable)) fail("Row " + line + " variable must be an ACS detailed-table estimate ID");
    if (!["acs1","acs5"].includes(series)) fail("Row " + line + " series must be acs1 or acs5");
    const start = integer(first, "Row " + line + " period_start");
    const end = integer(last, "Row " + line + " period_end");
    if (start < 2005 || end > 2100 || end - start !== (series === "acs5" ? 4 : 0) || (series === "acs1" && start === 2020))
      fail("Row " + line + " has an invalid or unsupported ACS period");
    const estimate = integer(rawEstimate, "Row " + line + " estimate", true);
    const moe = integer(rawMoe, "Row " + line + " moe", true);
    if (seen.has(source_id)) fail("Duplicate exact source_id at row " + line);
    seen.add(source_id);
    return {source_id,geography,variable,series,period_start:start,period_end:end,
      estimate,moe,estimate_raw:rawEstimate,moe_raw:rawMoe};
  });
}
export function readCsvBytes(buffer, declaredSize) {
  if (!(buffer instanceof ArrayBuffer) || buffer.byteLength > MAX_BYTES ||
      !Number.isSafeInteger(declaredSize) || declaredSize < 0 || declaredSize > MAX_BYTES ||
      declaredSize !== buffer.byteLength) fail("CSV file size invalid or exceeds 2,000,000 bytes");
  let text;
  try { text = new TextDecoder("utf-8", {fatal:true}).decode(buffer); }
  catch { fail("CSV must be valid UTF-8"); }
  return normalizeRows(parseCsv(text));
}
export async function fingerprintCsv(buffer, cryptoProvider = globalThis.crypto) {
  if (!(buffer instanceof ArrayBuffer) || buffer.byteLength > MAX_BYTES) fail("Cannot fingerprint invalid or oversized bytes");
  const byte_count = buffer.byteLength;
  if (!cryptoProvider?.subtle?.digest) return {sha256:null,byte_count,verification:"SHA-256 unavailable; source authenticity not verified"};
  const hash = await cryptoProvider.subtle.digest("SHA-256",buffer);
  const sha256 = Array.from(new Uint8Array(hash),byte=>byte.toString(16).padStart(2,"0")).join("");
  return {sha256,byte_count,verification:"Computed locally from original bytes; source authenticity not verified"};
}
export function compareRecords(records, leftId, rightId) {
  const left = records.find(x => x.source_id === leftId);
  const right = records.find(x => x.source_id === rightId);
  if (!left || !right || leftId === rightId) fail("Choose two different existing source IDs");
  const reasons = [], cautions = [];
  if (left.variable !== right.variable) reasons.push("Different measures cannot be directly compared");
  if (left.series !== right.series) reasons.push("ACS 1-year and 5-year series cannot be directly compared");
  if (left.geography !== right.geography) {
    if (left.period_start !== right.period_start || left.period_end !== right.period_end)
      reasons.push("Different geographies require the same period");
  } else {
    if (!(left.period_end < right.period_start || right.period_end < left.period_start))
      reasons.push("Same-geography periods overlap or are identical");
  }
  if (left.estimate === null || right.estimate === null) reasons.push("One or both estimates are missing");
  if (left.moe === null || right.moe === null) cautions.push("One or both margins of error are unavailable");
  cautions.push("Read ACS variable definitions, geography changes and margins of error; no statistical significance determination is made");
  return {left_id:leftId,right_id:rightId,comparable:reasons.length === 0,reasons,cautions,
    difference:reasons.length === 0 ? right.estimate - left.estimate : null};
}
export function evidenceExport(records, datasetLabel, comparison = null, sourceFile = null) {
  safeLabel(datasetLabel, "Dataset label");
  return {schema:"community-data-explorer/1",provenance_status:"user-supplied; not independently verified",
    dataset_label:datasetLabel,source_file:sourceFile,records,comparison,
    guidance:"Estimates are not determinations. Verify source, variable definitions, geography, vintage, and MOE before interpretation."};
}
