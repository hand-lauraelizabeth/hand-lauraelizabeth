import {buildHousingLedger, exportHousingJSON, HOUSING_JSON_LIMIT} from './housing-core.mjs';
const hasFields = (value, fields) => value && typeof value === 'object' && !Array.isArray(value) &&
  Object.keys(value).length === fields.length && fields.every(field => Object.hasOwn(value, field));
const rootFields = ['schema', 'sources', 'events', 'findings', 'disclaimer'];
const sourceFields = ['sourceId', 'kind', 'label', 'date'];
const eventFields = ['eventId', 'date', 'category', 'description', 'sourceIds', 'amountCents'];
const findingFields = ['eventId', 'kind'];

/** Reopen only the versioned, lossless local JSON produced by this tool. */
export function parseHousingJSON(text) {
  if (typeof text !== 'string' || !text.trim()) throw Error('JSON content is empty');
  let payload;
  try { payload = JSON.parse(text); }
  catch { throw Error('File does not contain valid JSON'); }
  if (!hasFields(payload, rootFields) || payload.schema !== 'housing-evidence-ledger-v1' ||
      !Array.isArray(payload.sources) || !Array.isArray(payload.events) || !Array.isArray(payload.findings)) {
    throw Error('Unsupported housing evidence JSON schema');
  }
  if (!payload.sources.every(s => hasFields(s, sourceFields)) ||
      !payload.events.every(e => hasFields(e, eventFields)) ||
      !payload.findings.every(f => hasFields(f, findingFields))) {
    throw Error('Housing evidence JSON contains missing or unexpected fields');
  }
  const ledger = buildHousingLedger({sources:payload.sources, events:payload.events});
  if (payload.disclaimer !== ledger.disclaimer ||
      payload.findings.length !== ledger.findings.length ||
      !payload.findings.every((f, i) => f.eventId === ledger.findings[i].eventId &&
                                          f.kind === ledger.findings[i].kind)) {
    throw Error('Housing evidence JSON review flags or disclaimer do not match the records');
  }
  // A compact JSON file can fit the input limit while its canonical, indented export does not.
  // Reject it before replacing the current tab with records that cannot be saved and reopened.
  exportHousingJSON(ledger);
  return ledger;
}

/** Validate metadata and actual bytes before decoding; never send file data to a server. */
export async function readHousingJSONFile(file) {
  if (!file || typeof file.name !== 'string' || !/\.json$/iu.test(file.name)) {
    throw Error('Choose a JSON export (.json)');
  }
  if (!Number.isSafeInteger(file.size) || file.size < 1 || file.size > HOUSING_JSON_LIMIT) {
    throw Error('JSON file must contain 1 to 5,000,000 bytes');
  }
  if (typeof file.arrayBuffer !== 'function') throw Error('Cannot read this file');
  const bytes = await file.arrayBuffer();
  if (!(bytes instanceof ArrayBuffer) || bytes.byteLength !== file.size) {
    throw Error('File bytes do not match the reported size');
  }
  let text;
  try { text = new TextDecoder('utf-8', {fatal:true}).decode(bytes); }
  catch { throw Error('JSON file must use valid UTF-8'); }
  return parseHousingJSON(text);
}
