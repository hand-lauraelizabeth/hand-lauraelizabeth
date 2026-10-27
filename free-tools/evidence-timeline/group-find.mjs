// Literal, case-sensitive search of user-assigned review groups; never changes evidence.
export function filterByGroupLabel(records, query='', ungroupedOnly=false) {
  if (!Array.isArray(records) || records.length > 10000) throw Error('Invalid group search records');
  if (typeof query !== 'string' || query.length > 120 || typeof ungroupedOnly !== 'boolean') throw Error('Invalid group search');
  return records.filter(row => {
    if (!row || typeof row.group !== 'string') throw Error('Invalid group search record');
    return ungroupedOnly ? row.group === '' : row.group.includes(query);
  });
}
