// Browser-local ACS comparison engine. No network calls or spreadsheet CSV export.
export const MAX_BYTES = 2_000_000;
export const MAX_RECORDS = 5_000;
export const COLUMNS = ["source_id","geography","variable","series","period_start","period_end","estimate","moe"];
const dangerous = /[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]/u;
const formulaPrefix = /^[\s\u00a0]*[=+\-@\uff1d\uff0b\uff0d\uff20]/u;
// Census annotation sentinels are not numeric estimates or numeric margins of error.
const annotationCodes = new Map([
  ["-999999999","suppressed_insufficient_cases"],
  ["-888888888","not_applicable"],
  ["-666666666","insufficient_observations"],
  ["-555555555","controlled_moe"],
  ["-333333333","open_interval_moe"],
  ["-222222222","insufficient_moe"]
]);
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
function integer(raw, field) {
  if (!/^(0|[1-9][0-9]*)$/.test(raw)) fail(field + " must be a nonnegative whole number");
  const n = Number(raw);
  if (!Number.isSafeInteger(n)) fail(field + " exceeds safe integer range");
  return n;
}
// ACS detailed-table variables such as B01002 median age have decimal estimates.
function measure(raw, field, kind) {
  if (raw === "" || raw === "null") return {value:null,status:"missing"};
  // Census documents sentinel values with .0 and .00 suffixes as well as integers.
  const code = raw.replace(/[.]0{1,2}$/, "");
  const annotation = annotationCodes.get(code);
  if (annotation) {
    if (kind === "estimate" && !["suppressed_insufficient_cases","not_applicable","insufficient_observations"].includes(annotation))
      fail(field + " contains an MOE-only annotation");
    return {value:null,status:annotation};
  }
  const symbols = kind === "estimate"
    ? {"N":"suppressed_insufficient_cases","(X)":"not_applicable","-":"insufficient_observations"}
    : {"N":"suppressed_insufficient_cases","(X)":"not_applicable","-":"insufficient_observations",
       "**":"insufficient_moe","***":"open_interval_moe","*****":"controlled_moe"};
  if (Object.hasOwn(symbols,raw)) return {value:null,status:symbols[raw]};
  if (!/^(0|[1-9][0-9]*)(?:[.][0-9]{1,6})?$/.test(raw))
    fail(field + " must be a nonnegative decimal (up to 6 places) or recognized ACS annotation");
  const [whole, fraction] = raw.split(".");
  if (BigInt(whole) > BigInt(Number.MAX_SAFE_INTEGER) ||
      (fraction !== undefined && BigInt(whole) > 1_000_000_000_000n))
    fail(field + " exceeds supported numeric precision");
  return {value:Number(raw),status:"available"};
}
function exactMeasureDifference(leftRaw, rightRaw) {
  const decimals = raw => (raw.split(".")[1] || "").length;
  const scale = Math.max(decimals(leftRaw), decimals(rightRaw));
  const scaled = raw => {
    const [whole, fraction = ""] = raw.split(".");
    return BigInt(whole) * 10n ** BigInt(scale) +
      BigInt((fraction + "0".repeat(scale - fraction.length)) || "0");
  };
  const diff = scaled(rightRaw) - scaled(leftRaw);
  if (scale === 0) return diff.toString();
  const sign = diff < 0n ? "-" : "";
  const digits = (diff < 0n ? -diff : diff).toString().padStart(scale + 1, "0");
  const whole = digits.slice(0, -scale);
  const fraction = digits.slice(-scale).replace(/0+$/, "");
  return sign + whole + (fraction ? "." + fraction : "");
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
    const {value:estimate,status:estimate_status} = measure(rawEstimate, "Row " + line + " estimate", "estimate");
    const {value:moe,status:moe_status} = measure(rawMoe, "Row " + line + " moe", "moe");
    if (seen.has(source_id)) fail("Duplicate exact source_id at row " + line);
    seen.add(source_id);
    return {source_id,geography,variable,series,period_start:start,period_end:end,
      estimate,moe,estimate_status,moe_status,estimate_raw:rawEstimate,moe_raw:rawMoe};
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
  const unavailable = reason => ({sha256:null,byte_count,
    verification:"SHA-256 unavailable (" + reason + "); source authenticity not verified"});
  if (!cryptoProvider?.subtle?.digest) return unavailable("Web Crypto not available");
  try {
    const hash = await cryptoProvider.subtle.digest("SHA-256",buffer);
    // SHA-256 is exactly 256 bits. Never label truncated or malformed bytes as a source fingerprint.
    if (!(hash instanceof ArrayBuffer) || hash.byteLength !== 32)
      return unavailable("invalid digest result");
    const sha256 = Array.from(new Uint8Array(hash),byte=>byte.toString(16).padStart(2,"0")).join("");
    return {sha256,byte_count,verification:"Computed locally from original bytes; source authenticity not verified"};
  } catch {
    return unavailable("digest failed");
  }
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
  if (left.moe === null || right.moe === null) cautions.push("One or both margins of error are unavailable or annotated (left: " + left.moe_status + "; right: " + right.moe_status + "). An annotated MOE is not a numeric zero.");
  cautions.push("Read ACS variable definitions, geography changes and margins of error; no statistical significance determination is made");
  const difference_exact = reasons.length === 0
    ? exactMeasureDifference(left.estimate_raw,right.estimate_raw) : null;
  return {left_id:leftId,right_id:rightId,comparable:reasons.length === 0,reasons,cautions,
    difference: difference_exact === null ? null : Number(difference_exact),difference_exact};
}
export function evidenceExport(records, datasetLabel, comparison = null, sourceFile = null) {
  safeLabel(datasetLabel, "Dataset label");
  return {schema:"community-data-explorer/1",provenance_status:"user-supplied; not independently verified",
    dataset_label:datasetLabel,source_file:sourceFile,records,comparison,
    guidance:"Estimates are not determinations. Verify source, variable definitions, geography, vintage, and MOE before interpretation."};
}
