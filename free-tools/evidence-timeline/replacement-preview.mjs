// Counts-only replacement preview. Never includes claims or source identifiers in dialog text.
const FIELDS = ['date', 'claim', 'status', 'kind', 'group'];
function assertUniqueSources(rows, label) {
  if (!Array.isArray(rows) || rows.length > 10000) throw Error('Invalid record list');
  const seen = new Set();
  for (const row of rows) {
    if (!row || typeof row !== 'object' || Array.isArray(row) || typeof row.sourceId !== 'string' || !row.sourceId.trim() || row.sourceId.length > 120) throw Error('Invalid source ID');
    if (seen.has(row.sourceId)) throw Error('Duplicate exact source ID in ' + label);
    seen.add(row.sourceId);
  }
}
export function previewReplacement(current, incoming) {
  assertUniqueSources(current, 'existing records');
  assertUniqueSources(incoming, 'incoming records');
  const existing = new Map(current.map(row => [row.sourceId, row]));
  const incomingIds = new Set(incoming.map(row => row.sourceId));
  let added = 0, changed = 0, unchanged = 0;
  for (const row of incoming) {
    const previous = existing.get(row.sourceId);
    if (!previous) added++;
    else if (FIELDS.some(field => previous[field] !== row[field])) changed++;
    else unchanged++;
  }
  let removed = 0;
  for (const row of current) if (!incomingIds.has(row.sourceId)) removed++;
  return { existing: current.length, incoming: incoming.length, added, removed, changed, unchanged };
}
export function replacementConfirmation(counts) {
  return 'Replace ' + counts.existing + ' records in this tab with ' + counts.incoming + ' imported records?\n\n' +
    counts.added + ' new; ' + counts.removed + ' removed; ' + counts.changed + ' changed under the same exact source ID; ' + counts.unchanged + ' unchanged.\n\n' +
    'This replaces the current working set. Export your existing records first if you need them. Cancel keeps all current records.';
}
