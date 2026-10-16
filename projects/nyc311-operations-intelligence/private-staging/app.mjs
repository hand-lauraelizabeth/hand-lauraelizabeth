import {validateDataset, selectCells, visibleProblemSeries} from './model.mjs';
const $ = id => document.getElementById(id);
let dataset = null;
const filters = ['month', 'borough', 'agency', 'query', 'sort'];
function setOptions(id, values) {
  const select = $(id), first = select.options[0].textContent;
  select.replaceChildren(new Option(first, ''));
  for (const value of [...new Set(values)].sort()) select.add(new Option(value, value));
  select.value = '';
}
function resetFilters() {
  for (const id of ['month','borough','agency','query']) $(id).value = '';
  $('sort').value = 'count';
}
function status(message, isError = false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', isError);
  $('status').setAttribute('role', isError ? 'alert' : 'status');
}
function render() {
  const cells = dataset ? selectCells(dataset.aggregates, Object.fromEntries(filters.map(id => [id, $(id).value]))) : [];
  $('result-count').textContent = dataset ? `${cells.length.toLocaleString()} released cells match the filters; suppressed cells remain excluded.` : 'Load data to explore results.';
  $('empty').hidden = !dataset || cells.length !== 0;
  const body = $('rows'); body.replaceChildren();
  for (const c of cells.slice(0, 1000)) {
    const tr = document.createElement('tr');
    for (const value of [c.month, c.borough, c.agency, c.problem, c.requests.toLocaleString()]) {
      const td = document.createElement('td'); td.textContent = value; tr.append(td);
    }
    tr.lastChild.className = 'num'; body.append(tr);
  }
  $('table-caption').textContent = !dataset ? 'No data loaded' : `Showing ${Math.min(cells.length,1000).toLocaleString()} of ${cells.length.toLocaleString()} matching released cells`;
  const bars = $('bars'); bars.replaceChildren();
  const series = visibleProblemSeries(cells), max = series[0]?.[1] || 1;
  for (const [name, count] of series) {
    const row = document.createElement('li'); row.className = 'barrow';
    const label = document.createElement('span'); label.textContent = name;
    const track = document.createElement('div'); track.className = 'track'; track.setAttribute('aria-hidden','true');
    const fill = document.createElement('div'); fill.className = 'fill'; fill.style.width = `${count / max * 100}%`;
    track.append(fill); const num = document.createElement('strong'); num.textContent = count.toLocaleString();
    row.append(label, track, num); bars.append(row);
  }
  if (cells.length > 1000) $('result-count').textContent += ' The table shows the first 1,000 matching cells; the chart uses all matching cells.';
}
function clearData() {
  dataset = null;
  $('file').value = '';
  for (const id of ['month','borough','agency']) setOptions(id, []);
  resetFilters();
  $('provenance').hidden = true;
  $('provenance').textContent = '';
  render();
}
function load(data, label) {
  const validated = validateDataset(data);
  dataset = validated;
  for (const id of ['month','borough','agency']) setOptions(id, dataset.aggregates.map(c => c[id]));
  resetFilters();
  status(`${label}: ${dataset.aggregates.length.toLocaleString()} disclosure-screened cells.`);
  $('provenance').textContent = `Snapshot as-of ${dataset.snapshot_as_of || 'not stated'}; declared source SHA-256 ${dataset.source_sha256} (not independently verified by this viewer).`;
  $('provenance').hidden = false;
  render();
}
$('file').addEventListener('change', async event => {
  const file = event.target.files?.[0]; if (!file) return;
  if (file.size > 8_000_000) { clearData(); status('Rejected: file exceeds the 8 MB local preview limit.', true); return; }
  try { load(JSON.parse(await file.text()), 'Local aggregate file'); }
  catch (error) { clearData(); status(`Rejected: ${error.message}`, true); }
});
$('demo').addEventListener('click', () => {
  $('file').value = '';
  const demo = {source:'Synthetic demonstration only', dataset_id:'erm2-nwe9', snapshot_as_of:'2026-10-15',
    source_sha256:'0'.repeat(64), source_bytes:0, rules:{display_minimum_cell_count:10},
    disclosure:{marginals_available:false}, aggregates:[
      {month:'2026-09',borough:'QUEENS',agency:'DOT',problem:'Road',requests:40},
      {month:'2026-09',borough:'BROOKLYN',agency:'DOT',problem:'Road',requests:35},
      {month:'2026-09',borough:'MANHATTAN',agency:'DEP',problem:'Water',requests:22},
      {month:'2026-08',borough:'QUEENS',agency:'NYPD',problem:'Noise',requests:55}
    ]}; load(demo, 'SYNTHETIC EXAMPLE — NOT NYC DATA');
});
$('clear').addEventListener('click', () => {clearData();status('No dataset loaded.');});
$('reset').addEventListener('click', () => {resetFilters();render();});
for (const id of filters) $(id).addEventListener('input', render);
render();
