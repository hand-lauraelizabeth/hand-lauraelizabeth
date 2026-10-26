// Review classifications are user-assigned; changing one never alters source identity or evidence text.
import {normalizeExact} from './exact-core.mjs';
export const STATUS_OPTIONS = Object.freeze(['reported','corroborated','disputed','unresolved']);
export function updateReviewStatus(records, sourceId, status) {
  if(typeof sourceId!=='string'||!STATUS_OPTIONS.includes(status)) throw Error('Invalid review status update');
  const original=normalizeExact(records);
  if(!original.some(row=>row.sourceId===sourceId)) throw Error('Source ID not found');
  return normalizeExact(original.map(row=>row.sourceId===sourceId?{...row,status}:row));
}
