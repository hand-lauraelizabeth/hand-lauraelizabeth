/* Local-only comparison UI for two CSV/TSV files. No network calls. */
(function (root) {
  'use strict';
  const $ = id => document.getElementById(id);
  const lib = root.DataRescue;
  const engine = root.DataRescueProvenance || root.DataReconcile;
  let first = null, second = null, firstName = '', secondName = '';
  let comparison = null, generation = 0;
  const el = (tag, text) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = String(text);
    return node;
  };
  function message(text, error = false) {
    const node = $('compareStatus');
    node.textContent = text;
    node.className = error ? 'error' : '';
  }
  function options(selectId, data) {
    const select = $(selectId);
    select.replaceChildren();
    select.append(el('option', 'Select a column'));
    select.options[0].value = '';
    for (const name of (data ? data.normalizedHeaders : [])) {
      const opt = el('option', name);
      opt.value = name;
      select.append(opt);
    }
    select.disabled = !data;
  }
  function invalidate() {
    comparison = null;
    $('compareMetrics').replaceChildren();
    $('compareResults').replaceChildren();
    $('compareExport').disabled = true;
    $('compareExportJson').disabled = true;
    $('compareRun').disabled = !(first && second && $('leftKey').value && $('rightKey').value);
  }
  function setPrimary(data, name = '') {
    // Every primary replacement changes the source pair, even when headers match.
    // Invalidate in-flight second-file reads and revoke all prior comparison evidence.
    const priorKey = $('leftKey').value;
    ++generation;
    first = data;
    firstName = name;
    second = null;
    secondName = '';
    $('compareFile').value = '';
    options('leftKey', data);
    if (data && priorKey && data.normalizedHeaders.includes(priorKey)) $('leftKey').value = priorKey;
    options('rightKey', null);
    invalidate();
    message(data ? 'First file ready. Choose a second file and both identifier columns.' : 'Open a first file above to compare.');
  }
  function clearSecond() {
    generation++;
    second = null;
    secondName = '';
    $('compareFile').value = '';
    options('rightKey', null);
    invalidate();
    message(first ? 'Second file cleared. Choose a second CSV or TSV.' : 'Open a first file above to compare.');
  }
  async function loadSecond() {
    const file = $('compareFile').files && $('compareFile').files[0];
    const thisGeneration = ++generation;
    second = null;
    options('rightKey', null);
    invalidate();
    if (!file) { message('No second file selected.'); return; }
    if (file.size > lib.MAX_BYTES) {
      message('The second file is larger than 5 MB.', true); return;
    }
    if (!/\.(csv|tsv)$/i.test(file.name)) {
      message('Choose a second .csv or .tsv file.', true); return;
    }
    message('Reading second file locally…');
    try {
      if (!root.DataRescueFileReader || typeof root.DataRescueFileReader.read !== 'function')
        throw Error('Secure local file reader is unavailable. Reload the page.');
      // Never fall back to File.text(): it bypasses byte-count and fatal UTF-8 validation.
      const parsed = await root.DataRescueFileReader.read(file, lib.parseDelimited);
      if (thisGeneration !== generation) return;
      second = parsed;
      secondName = file.name;
      options('rightKey', second);
      invalidate();
      message('Loaded second file: ' + second.rows.length + ' rows. No file was transmitted.');
    } catch (error) {
      if (thisGeneration !== generation) return;
      message('Unable to read second file: ' + error.message, true);
    }
  }
  function auditRows(result) {
    const records = [];
    const add = (kind, key, a, b) => records.push([kind, key, a, b]);
    result.matches.forEach(item => add('Match', item.key, item.leftRow, item.rightRow));
    result.ambiguous.forEach(item => add('Ambiguous — not merged', item.key, item.leftRows.join('; '), item.rightRows.join('; ')));
    result.leftOnly.forEach(item => add('First file only', item.key, item.row, ''));
    result.rightOnly.forEach(item => add('Second file only', item.key, '', item.row));
    result.missingLeft.forEach(row => add('Missing first-file key', '', row, ''));
    result.missingRight.forEach(row => add('Missing second-file key', '', '', row));
    return records;
  }
  function render(result, coverage) {
    const categories = [
      ['One-to-one matches', result.matches.length],
      ['Ambiguous keys', result.ambiguous.length],
      ['First file only', result.leftOnly.length],
      ['Second file only', result.rightOnly.length],
      ['Missing identifiers', result.missingLeft.length + result.missingRight.length],
      ['First-file records classified', coverage.first.total],
      ['Second-file records classified', coverage.second.total],
      ['First-file records in ambiguous groups', coverage.first.ambiguous],
      ['Second-file records in ambiguous groups', coverage.second.ambiguous]
    ];
    const grid = $('compareMetrics');
    grid.replaceChildren();
    for (const [name, count] of categories) {
      const metric = el('div');
      metric.className = 'metric';
      metric.append(el('span', name), el('strong', count));
      grid.append(metric);
    }
    const rows = auditRows(result);
    const table = el('table');
    table.append(el('caption', 'First ' + Math.min(30, rows.length) + ' of ' + rows.length + ' reconciliation findings'));
    const head = el('thead'), heading = el('tr');
    ['Classification', 'Identifier', 'First-file row(s)', 'Second-file row(s)'].forEach(text => heading.append(el('th', text)));
    head.append(heading); table.append(head);
    const body = el('tbody');
    rows.slice(0, 30).forEach(record => {
      const line = el('tr');
      record.forEach(value => line.append(el('td', value)));
      body.append(line);
    });
    table.append(body);
    $('compareResults').replaceChildren(table);
    $('compareExport').disabled = false;
    $('compareExportJson').disabled = false;
    message('Comparison complete: ' + result.matches.length + ' exact one-to-one matches; ' + result.ambiguous.length + ' ambiguous identifier groups. First-file records classified: ' + coverage.first.total + ' of ' + first.rows.length + '; second-file records classified: ' + coverage.second.total + ' of ' + second.rows.length + '. Unmatched and missing-key records remain separate.');
  }
  function compare() {
    if (!(first && second && $('leftKey').value && $('rightKey').value)) return;
    try {
      comparison = (engine.compare || engine.reconcile)(first, second, $('leftKey').value, $('rightKey').value);
      const coverage = root.DataRescueReconciliationEvidence.summarizeCoverage(comparison);
      if (coverage.first.total !== first.rows.length || coverage.second.total !== second.rows.length)
        throw Error('Comparison did not account for every record in both files.');
      render(comparison, coverage);
    } catch (error) {
      invalidate();
      message('Unable to compare: ' + error.message, true);
    }
  }
  function exportAudit() {
    if (!comparison) return;
    const rows = auditRows(comparison);
    const headers = ['Classification', 'Identifier', 'First-file row(s)', 'Second-file row(s)'];
    const parsed = {headers, normalizedHeaders: headers, rows, warnings: [], delimiter: ','};
    // Identifier values are untrusted. Spreadsheet-oriented mitigation is explicit and imperfect.
    const csv = lib.exportCsvDownload(parsed, true);
    const url = URL.createObjectURL(new Blob([csv], {type: 'text/csv;charset=utf-8'}));
    const link = el('a');
    link.href = url;
    link.download = 'data-rescue-comparison-audit.csv';
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    message('Exported ' + rows.length + ' findings for ' + firstName + ' and ' + secondName + '. Contains identifier keys and source row numbers, not full records. Keep the file private if identifiers are sensitive.');
  }
  function exportExactAuditJson() {
    if (!comparison) return;
    const json = root.DataRescueReconciliationEvidence.exportJson(comparison, {
      firstName, secondName, firstKey: $('leftKey').value, secondKey: $('rightKey').value
    });
    const url = URL.createObjectURL(new Blob([json], {type:'application/json;charset=utf-8'}));
    const link = el('a');
    link.href = url;
    link.download = 'data-rescue-comparison-evidence.json';
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    message('Exported exact decoded identifiers and source-record positions for ' + firstName + ' and ' + secondName + '. No input records were merged. This local JSON contains sensitive identifiers if your files do; it is not source authentication.');
  }
  $('compareFile').addEventListener('change', loadSecond);
  $('compareClear').addEventListener('click', clearSecond);
  $('leftKey').addEventListener('change', invalidate);
  $('rightKey').addEventListener('change', invalidate);
  $('compareRun').addEventListener('click', compare);
  $('compareExport').addEventListener('click', exportAudit);
  $('compareExportJson').addEventListener('click', exportExactAuditJson);
  root.DataRescueCompareUI = {setPrimary};
})(window);
