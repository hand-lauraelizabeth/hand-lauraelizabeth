export function uniqueIds(records) {
  const ids = records.map(record => record.id);
  return ids.length === new Set(ids).size;
}
