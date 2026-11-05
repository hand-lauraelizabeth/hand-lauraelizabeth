/** Strict, local-only reopening of this tool's versioned JSON exports. */
import {validateWorkspace} from './core.mjs';
import {assertUniqueJSONKeys} from './strict-json.mjs';
export const MAX_IMPORT_BYTES = 5_000_000;
const REQUEST_KEYS = ['id','jurisdiction','agency','stage','submittedOn','agencyTrackingId','description'];
const EVENT_KEYS = ['id','requestId','date','kind','sourceId','description'];
function exactKeys(object, keys, label) {
  if (!object || typeof object !== 'object' || Array.isArray(object)) throw new Error(`Invalid ${label}`);
  const actual = Object.keys(object);
  if (actual.length !== keys.length || actual.some(key => !keys.includes(key))) {
    throw new Error(`Unexpected or missing ${label} fields; nothing imported`);
  }
}
export function parseWorkspaceJSON(source) {
  if (typeof source !== 'string' || source.includes('\0')) throw new Error('Invalid JSON text');
  assertUniqueJSONKeys(source);
  let raw;
  try { raw = JSON.parse(source); } catch { throw new Error('Invalid JSON syntax'); }
  exactKeys(raw, ['version','requests','events'], 'workspace');
  if (!Array.isArray(raw.requests) || !Array.isArray(raw.events)) throw new Error('Invalid workspace collections');
  if (raw.requests.length > 1000 || raw.events.length > 10000) throw new Error('Workspace record limit exceeded');
  for (const request of raw.requests) exactKeys(request, REQUEST_KEYS, 'request');
  for (const event of raw.events) exactKeys(event, EVENT_KEYS, 'event');
  return validateWorkspace(raw);
}
export async function readWorkspaceFile(file) {
  if (!file || typeof file.name !== 'string' || !/\.json$/i.test(file.name)) throw new Error('Choose a .json workspace export');
  if (file.type && !['application/json','text/json','application/octet-stream'].includes(file.type)) throw new Error('Unsupported file type');
  if (!Number.isSafeInteger(file.size) || file.size < 0 || file.size > MAX_IMPORT_BYTES) throw new Error('JSON file exceeds 5 MB limit');
  if (typeof file.arrayBuffer !== 'function') throw new Error('File cannot be read');
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (bytes.byteLength > MAX_IMPORT_BYTES) throw new Error('JSON file exceeds 5 MB limit');
  if (bytes.byteLength !== file.size) throw new Error('JSON file size mismatch; nothing imported');
  let source;
  try { source = new TextDecoder('utf-8', {fatal:true}).decode(bytes); }
  catch { throw new Error('File is not valid UTF-8'); }
  return parseWorkspaceJSON(source);
}
