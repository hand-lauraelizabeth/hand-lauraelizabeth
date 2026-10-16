// Public aggregate schema guard. Reject raw or insufficiently suppressed records.
const TOP = new Set(['source', 'dataset_id', 'snapshot_as_of', 'source_sha256', 'source_bytes', 'rules', 'disclosure', 'aggregates']);
const CELL = new Set(['month', 'borough', 'agency', 'problem', 'requests', 'closed_with_valid_interval']);
const BOROUGHS = new Set(['BRONX', 'BROOKLYN', 'MANHATTAN', 'QUEENS', 'STATEN ISLAND', 'UNKNOWN']);
export function validateDataset(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw Error('Expected an aggregate JSON object.');
  if (Object.keys(data).some(k => !TOP.has(k))) throw Error('Unexpected top-level fields; do not load source records or private QA.');
  if (data.dataset_id !== 'erm2-nwe9' || !/^[a-f0-9]{64}$/i.test(data.source_sha256 || '')) throw Error('Invalid dataset provenance.');
  const min = data.rules?.display_minimum_cell_count;
  if (!Number.isInteger(min) || min < 10 || data.disclosure?.marginals_available !== false) throw Error('Disclosure metadata is missing or unsafe.');
  if (!Array.isArray(data.aggregates) || data.aggregates.length > 100000) throw Error('Invalid aggregate collection.');
  const seen = new Set();
  for (const c of data.aggregates) {
    if (!c || typeof c !== 'object' || Object.keys(c).some(k => !CELL.has(k))) throw Error('Raw or unexpected cell fields detected.');
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(c.month) || !BOROUGHS.has(c.borough) ||
        typeof c.agency !== 'string' || !c.agency || typeof c.problem !== 'string' || !c.problem ||
        !Number.isSafeInteger(c.requests) || c.requests < min) throw Error('Invalid or undersized aggregate cell.');
    const key = JSON.stringify([c.month, c.borough, c.agency, c.problem]);
    if (seen.has(key)) throw Error('Duplicate aggregate grain.');
    seen.add(key);
    if ('closed_with_valid_interval' in c && (!Number.isSafeInteger(c.closed_with_valid_interval) ||
        c.closed_with_valid_interval < min || c.requests - c.closed_with_valid_interval < min))
      throw Error('Closure partition fails disclosure threshold.');
  }
  return data;
}
export function selectCells(cells, {month = '', borough = '', agency = '', query = '', sort = 'count'} = {}) {
  const q = query.trim().toLocaleLowerCase();
  const filtered = cells.filter(c => (!month || c.month === month) && (!borough || c.borough === borough) &&
    (!agency || c.agency === agency) && (!q || c.problem.toLocaleLowerCase().includes(q)));
  return filtered.sort((a, b) => sort === 'name' ? a.problem.localeCompare(b.problem) || a.month.localeCompare(b.month) :
    b.requests - a.requests || a.problem.localeCompare(b.problem));
}
export function visibleProblemSeries(cells, limit = 8) {
  const totals = new Map();
  for (const c of cells) totals.set(c.problem, (totals.get(c.problem) || 0) + c.requests);
  return [...totals].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, limit);
}
