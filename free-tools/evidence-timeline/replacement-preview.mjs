// Counts-only replacement preview. Never includes claims or source identifiers in dialog text.
const FIELDS = ['date', 'claim', 'status', 'kind', 'group'];
export function previewReplacement(current, incoming) {
  if (!Array.isArray(current) || !Array.isArray(incoming)) throw Error('Expected record arrays');
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
