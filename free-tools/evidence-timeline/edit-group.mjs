// User-assigned related-record groups are review metadata, not verified findings.
// Preserve exact source identifiers and evidence; validate the entire ledger atomically.
import {normalizeExact} from './exact-core.mjs';

export function setReviewGroup(records, sourceId, group) {
  if (typeof sourceId !== 'string' || !sourceId ||
      typeof group !== 'string' || group.length > 120) {
    throw Error('Invalid related-record group update');
  }
  const original = normalizeExact(records);
  if (!original.some(row => row.sourceId === sourceId)) throw Error('Source ID not found');
  return normalizeExact(original.map(row => row.sourceId === sourceId ? {...row, group} : row));
}
