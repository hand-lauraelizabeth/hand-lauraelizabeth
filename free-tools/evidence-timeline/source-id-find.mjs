// Find literal source-ID fragments without rewriting evidence or source identifiers.
import {filterReviewRows} from './review-filter.mjs';

export function findSourceIds(records, status='all', query='') {
  if (typeof query !== 'string' || query.length > 120) throw Error('Invalid source ID search');
  const visible = filterReviewRows(records, status);
  return query === '' ? visible : visible.filter(row => typeof row.sourceId === 'string' && row.sourceId.includes(query));
}
