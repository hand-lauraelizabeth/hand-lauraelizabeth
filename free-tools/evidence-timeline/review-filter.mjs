// Browser-local chronology filtering. Never changes the records or export data.
export const REVIEW_STATUSES = Object.freeze(['reported','corroborated','disputed','unresolved']);
export function filterReviewRows(records, status='all') {
  if (!Array.isArray(records)) throw Error('Invalid record list');
  if (status!=='all' && !REVIEW_STATUSES.includes(status)) throw Error('Unknown review status');
  return status==='all' ? records.slice() : records.filter(row=>row.status===status);
}
export function reviewStatusSummary(records) {
  if (!Array.isArray(records)) throw Error('Invalid record list');
  const counts=Object.fromEntries(REVIEW_STATUSES.map(status=>[status,0]));
  for (const row of records) {
    if (!row || !Object.hasOwn(counts,row.status)) throw Error('Unknown record status');
    counts[row.status]++;
  }
  return 'Reported: '+counts.reported+' · Corroborated: '+counts.corroborated+
    ' · Disputed: '+counts.disputed+' · Unresolved: '+counts.unresolved+'. Statuses are user-assigned.';
}
